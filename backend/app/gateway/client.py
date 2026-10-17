"""LLM gateway: OpenAI, primary model (gpt-4o) with fallback model (gpt-4o-mini) and a fallback API key;
Groq (gpt-oss) as the last-resort provider when GROQ_FALLBACK_API_KEY is set.

With PORTKEY_API_KEY, requests go through Portkey (retry, cache, fallback) using the same
gateway config shape as the 8hr-MARATHON template; the two Portkey integrations hold the
primary and the fallback OpenAI key. Without Portkey, the client calls OpenAI directly and
tries each model with the primary key, then the fallback key.
"""

import json
import re
import time
from dataclasses import dataclass

import logfire

from app.config import settings

GATEWAY_CONFIG = {
    "strategy": {"mode": "fallback"},
    "cache": {"mode": "simple"},
    "retry": {"attempts": 2, "on_status_codes": [429, 503]},
    "targets": [
        {"override_params": {"model": f"@{settings.PORTKEY_SLUG}/{settings.PRIMARY_MODEL}"}},
        {"override_params": {"model": f"@{settings.PORTKEY_SLUG_2}/{settings.PRIMARY_MODEL}"}},
        {"override_params": {"model": f"@{settings.PORTKEY_SLUG}/{settings.FALLBACK_MODEL}"}},
        {"override_params": {"model": f"@{settings.PORTKEY_SLUG_2}/{settings.FALLBACK_MODEL}"}},
    ],
}
# Small tier for fast classifiers (safety gate, planner): small model first, large as fallback.
GATEWAY_CONFIG_SMALL = {**GATEWAY_CONFIG, "targets": GATEWAY_CONFIG["targets"][2:] + GATEWAY_CONFIG["targets"][:2]}


class LLMUnavailable(RuntimeError):
    pass


@dataclass
class LLMResult:
    text: str
    model: str
    via: str  # "portkey" | "openai" | "openai-fallback-key"
    ms: float
    cache: str = "MISS"


_portkey: dict[str, object] = {}
_openai: dict[str, object] = {}


def _portkey_client(tier: str = "default"):
    if tier not in _portkey:
        from portkey_ai import Portkey

        _portkey[tier] = Portkey(api_key=settings.PORTKEY_API_KEY, config=GATEWAY_CONFIG_SMALL if tier == "small" else GATEWAY_CONFIG)
    return _portkey[tier]


def _openai_client(key: str, base_url: str | None = None):
    if key not in _openai:
        from openai import OpenAI

        _openai[key] = OpenAI(api_key=key, base_url=base_url or settings.OPENAI_BASE_URL, max_retries=2, timeout=90)
    return _openai[key]


def attempts(tier: str = "default") -> list[tuple[str, str, str]]:
    """(api_key, model, label) in the order they are tried: OpenAI models × keys, then Groq."""
    keys = [(k, label) for k, label in ((settings.OPENAI_API_KEY, "openai"), (settings.OPENAI_FALLBACK_API_KEY, "openai-fallback-key")) if k]
    models = [settings.PRIMARY_MODEL, settings.FALLBACK_MODEL]
    groq = [settings.GROQ_MODEL, settings.GROQ_SMALL_MODEL]
    if tier == "small":
        models.reverse()
        groq.reverse()
    out = [(k, m, label) for m in dict.fromkeys(models) for k, label in keys]
    if settings.GROQ_FALLBACK_API_KEY:
        out += [(settings.GROQ_FALLBACK_API_KEY, m, "groq") for m in dict.fromkeys(groq)]
    return out


def _cache_status(resp) -> str:
    for attr in ("_raw_response", "_response", "_http_response"):
        raw = getattr(resp, attr, None)
        if raw is not None:
            status = getattr(raw, "headers", {}).get("x-portkey-cache-status", "")
            if status:
                return status.upper()
    return "MISS"


def chat(messages: list[dict], *, json_mode: bool = False, temperature: float = 0.1, feature: str = "assess",
         max_tokens: int = 4096, tier: str = "default") -> LLMResult:
    """tier="small": the fallback (small) model first, for fast classification."""
    if not settings.llm_configured:
        raise LLMUnavailable("No LLM configured: set OPENAI_API_KEY (and optionally OPENAI_FALLBACK_API_KEY) in backend/.env")
    kwargs: dict = {"messages": messages, "temperature": temperature, "max_completion_tokens": max_tokens}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    start = time.perf_counter()
    with logfire.span("llm {feature}", feature=feature):
        if settings.PORTKEY_API_KEY:
            resp = _portkey_client(tier).with_options(metadata={"feature": feature, "_user": "spectrasense"}).chat.completions.create(**kwargs)
            return LLMResult(resp.choices[0].message.content or "", getattr(resp, "model", "portkey"), "portkey",
                             (time.perf_counter() - start) * 1000, _cache_status(resp))

        last: Exception | None = None
        for key, model, label in attempts(tier):
            try:
                if label == "groq":  # gpt-oss reasons before answering; keep it short so max tokens go to the answer
                    resp = _openai_client(key, settings.GROQ_BASE_URL).chat.completions.create(model=model, reasoning_effort="low", **kwargs)
                else:
                    resp = _openai_client(key).chat.completions.create(model=model, **kwargs)
                return LLMResult(resp.choices[0].message.content or "", model, label, (time.perf_counter() - start) * 1000)
            except Exception as e:  # noqa: BLE001 - try the next key / model
                logfire.warning("{label} {model} failed: {err}", label=label, model=model, err=str(e))
                last = e
        raise LLMUnavailable(f"All LLM targets failed: {last}")


def parse_json(text: str) -> dict:
    """Parse a JSON object, tolerating code fences or prose around it."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise
        return json.loads(m.group(0))
