"""LLM gateway: the active provider (LLM_PROVIDER = groq | openai), each with a large and a small
model and a primary and a fallback API key.

Direct mode tries each model with the primary key, then the fallback key; then, only if
LLM_FALLBACK_PROVIDER is set, the same on the other provider. With PORTKEY_API_KEY, requests go
through Portkey (retry, cache, fallback) using the 8hr-MARATHON template's gateway config shape;
the two Portkey integrations hold the primary and the fallback key.
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
    via: str  # "portkey" | "openai" | "openai-fallback-key" | "groq" | "groq-fallback-key"
    ms: float
    cache: str = "MISS"
    tokens: int = 0


# Tokens used by this process, per model (the batch runner reports them per case).
USAGE: dict[str, int] = {}


def _count(resp, model: str) -> int:
    n = int(getattr(getattr(resp, "usage", None), "total_tokens", 0) or 0)
    USAGE[model] = USAGE.get(model, 0) + n
    return n


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    keys: tuple[tuple[str, str], ...]  # (api_key, label)
    large: str
    small: str


def provider(name: str) -> Provider | None:
    if name == "openai":
        keys = ((settings.OPENAI_API_KEY, "openai"), (settings.OPENAI_FALLBACK_API_KEY, "openai-fallback-key"))
        return Provider("openai", settings.OPENAI_BASE_URL, tuple((k, lb) for k, lb in keys if k),
                        settings.OPENAI_MODEL, settings.OPENAI_SMALL_MODEL)
    if name == "groq":
        keys = ((settings.GROQ_API_KEY, "groq"), (settings.GROQ_FALLBACK_API_KEY, "groq-fallback-key"))
        return Provider("groq", settings.GROQ_BASE_URL, tuple((k, lb) for k, lb in keys if k),
                        settings.GROQ_MODEL, settings.GROQ_SMALL_MODEL)
    return None


def providers() -> list[Provider]:
    """Active provider first; the fallback provider only when LLM_FALLBACK_PROVIDER names a different one."""
    names = [settings.LLM_PROVIDER]
    if settings.LLM_FALLBACK_PROVIDER and settings.LLM_FALLBACK_PROVIDER != settings.LLM_PROVIDER:
        names.append(settings.LLM_FALLBACK_PROVIDER)
    return [p for p in map(provider, names) if p and p.keys]


_portkey: dict[str, object] = {}
_openai: dict[tuple[str, str], object] = {}


def _portkey_client(tier: str = "default"):
    if tier not in _portkey:
        from portkey_ai import Portkey

        _portkey[tier] = Portkey(api_key=settings.PORTKEY_API_KEY, config=GATEWAY_CONFIG_SMALL if tier == "small" else GATEWAY_CONFIG)
    return _portkey[tier]


def _openai_client(key: str, base_url: str):
    if (key, base_url) not in _openai:
        from openai import OpenAI

        # Groq's free tier rate-limits per minute; the SDK honours retry-after, so allow more retries there.
        retries = 4 if "groq.com" in base_url else 2
        _openai[(key, base_url)] = OpenAI(api_key=key, base_url=base_url, max_retries=retries, timeout=90)
    return _openai[(key, base_url)]


def attempts(tier: str = "default") -> list[tuple[str, str, str, str]]:
    """(api_key, model, label, base_url) in the order they are tried: per provider, models × keys."""
    out = []
    for p in providers():
        models = [p.small, p.large] if tier == "small" else [p.large, p.small]
        out += [(k, m, label, p.base_url) for m in dict.fromkeys(models) for k, label in p.keys]
    return out


def _extra(model: str) -> dict:
    # Reasoning models on Groq (gpt-oss, qwen3) think before answering; keep it short so max tokens go to the answer.
    return {"reasoning_effort": "low"} if any(s in model for s in ("gpt-oss", "qwen3")) else {}


def _rate_limited(e: Exception | None) -> bool:
    return e is not None and bool(re.search(r"\b429\b|rate limit", str(e), re.I))


def _retry_after(e: Exception | None, cap: float = 30.0) -> float:
    """Seconds the provider asks to wait ("Please try again in 12.5s" / "in 1m3s"), capped."""
    m = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", str(e or ""))
    secs = (int(m.group(1) or 0) * 60 + float(m.group(2))) if m else 10.0
    return min(max(secs, 1.0), cap)


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
    """tier="small": the small model first, for fast classification."""
    if not settings.llm_configured:
        raise LLMUnavailable("No LLM configured: set GROQ_API_KEY or OPENAI_API_KEY (see LLM_PROVIDER) in backend/.env")
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
        for _round in range(2):  # a second round only after every target was rate-limited
            if _round and not _rate_limited(last):
                break
            if _round:
                wait = _retry_after(last)
                logfire.warning("all LLM targets rate-limited; waiting {s} s", s=wait)
                time.sleep(wait)
            for key, model, label, base_url in attempts(tier):
                try:
                    try:
                        resp = _openai_client(key, base_url).chat.completions.create(model=model, **kwargs, **_extra(model))
                    except Exception as e:  # noqa: BLE001
                        # Groq rejects JSON-mode output it cannot validate ("Failed to generate JSON"); the prompts
                        # already ask for JSON and parse_json tolerates stray text, so retry once without JSON mode.
                        if not (json_mode and re.search(r"failed to generate json|json_validate_failed", str(e), re.I)):
                            raise
                        plain = {k: v for k, v in kwargs.items() if k != "response_format"}
                        resp = _openai_client(key, base_url).chat.completions.create(model=model, **plain, **_extra(model))
                    return LLMResult(resp.choices[0].message.content or "", model, label, (time.perf_counter() - start) * 1000,
                                     tokens=_count(resp, model))
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
