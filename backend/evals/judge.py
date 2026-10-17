"""Judge LLM for the evals.

Uses its own Groq key (JUDGE_GROQ) so grading never rate-limits the live app, as in the
8hr-MARATHON template. Without JUDGE_GROQ it falls back to the app's gateway, so the evals
still run with one key; the report records which route was used.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import settings
from app.gateway import chat, parse_json

JUDGE_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class JudgeUnavailable(RuntimeError):
    pass


@dataclass
class Judge:
    calls: int = 0
    route: str = field(default="")
    _client: object | None = None

    def __post_init__(self) -> None:
        if settings.JUDGE_GROQ:
            from openai import OpenAI

            self._client = OpenAI(api_key=settings.JUDGE_GROQ, base_url=GROQ_BASE_URL, max_retries=2, timeout=90)
            self.route = f"groq:{JUDGE_MODEL} (JUDGE_GROQ)"
        elif settings.llm_configured:
            self.route = "app gateway (no JUDGE_GROQ set)"
        else:
            raise JudgeUnavailable("No judge LLM: set JUDGE_GROQ (or GROQ_API_KEY / PORTKEY_API_KEY) in backend/.env")

    def ask(self, system: str, user: str) -> dict:
        """One JSON-mode call at temperature 0."""
        self.calls += 1
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        if self._client is not None:
            resp = self._client.chat.completions.create(  # type: ignore[attr-defined]
                model=JUDGE_MODEL, messages=messages, temperature=0, max_tokens=2048,
                response_format={"type": "json_object"},
            )
            return parse_json(resp.choices[0].message.content or "{}")
        return parse_json(chat(messages, json_mode=True, temperature=0, feature="eval-judge", max_tokens=2048).text)
