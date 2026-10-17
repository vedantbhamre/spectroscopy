"""LLM gateway: Portkey (routing, retry, cache, fallback) → Groq Llama 3.3 70B, fallback Llama 3.1 8B.

Same gateway config as the 8hr-MARATHON template. Without PORTKEY_API_KEY the client calls
Groq's OpenAI-compatible API directly and applies the same fallback order itself.
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
        {"override_params": {"model": f"@{settings.GROQ_SLUG}/{settings.PRIMARY_MODEL}"}},
        {"override_params": {"model": f"@{settings.GROQ_SLUG_2}/{settings.FALLBACK_MODEL}"}},
    ],
}
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class LLMUnavailable(RuntimeError):
    pass


@dataclass
class LLMResult:
    text: str
    model: str
    via: str  # "portkey" | "groq"
    ms: float
    cache: str = "MISS"


_portkey = None
_groq: dict[str, object] = {}


def _portkey_client():
    global _portkey
    if _portkey is None:
        from portkey_ai import Portkey

        _portkey = Portkey(api_key=settings.PORTKEY_API_KEY, config=GATEWAY_CONFIG)
    return _portkey


def _groq_client(key: str):
    if key not in _groq:
        from openai import OpenAI

        _groq[key] = OpenAI(api_key=key, base_url=GROQ_BASE_URL, max_retries=2, timeout=60)
    return _groq[key]


def _cache_status(resp) -> str:
    for attr in ("_raw_response", "_response", "_http_response"):
        raw = getattr(resp, attr, None)
        if raw is not None:
            status = getattr(raw, "headers", {}).get("x-portkey-cache-status", "")
            if status:
                return status.upper()
    return "MISS"


def chat(messages: list[dict], *, json_mode: bool = False, temperature: float = 0.1, feature: str = "assess", max_tokens: int = 4096) -> LLMResult:
    if not settings.llm_configured:
        raise LLMUnavailable("No LLM configured: set PORTKEY_API_KEY or GROQ_API_KEY in backend/.env")
    kwargs: dict = {"messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    start = time.perf_counter()
    with logfire.span("llm {feature}", feature=feature):
        if settings.PORTKEY_API_KEY:
            resp = _portkey_client().with_options(metadata={"feature": feature, "_user": "spectrasense"}).chat.completions.create(**kwargs)
            return LLMResult(resp.choices[0].message.content or "", getattr(resp, "model", "portkey"), "portkey",
                             (time.perf_counter() - start) * 1000, _cache_status(resp))

        attempts = [(settings.GROQ_API_KEY, settings.PRIMARY_MODEL),
                    (settings.GROQ_FALLBACK_API_KEY or settings.GROQ_API_KEY, settings.FALLBACK_MODEL)]
        last: Exception | None = None
        for key, model in attempts:
            try:
                resp = _groq_client(key).chat.completions.create(model=model, **kwargs)
                return LLMResult(resp.choices[0].message.content or "", model, "groq", (time.perf_counter() - start) * 1000)
            except Exception as e:  # noqa: BLE001 - try the fallback model
                logfire.warning("groq {model} failed: {err}", model=model, err=str(e))
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
