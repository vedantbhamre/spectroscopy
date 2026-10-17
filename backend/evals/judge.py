"""Judge LLM for the evals.

Uses its own key so grading never rate-limits the live app, as in the 8hr-MARATHON template:
JUDGE_OPENAI_API_KEY (JUDGE_MODEL, default gpt-4o), else JUDGE_GROQ (gpt-oss-120b on Groq).
Without either it falls back to the app's gateway, so the evals still run with one key;
the report records which route was used.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import settings
from app.gateway import chat, parse_json

GROQ_JUDGE_MODEL = "openai/gpt-oss-120b"


class JudgeUnavailable(RuntimeError):
    pass


@dataclass
class Judge:
    calls: int = 0
    route: str = field(default="")
    model: str = field(default="")
    _client: object | None = None
    _extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        from openai import OpenAI

        if settings.JUDGE_OPENAI_API_KEY:
            self._client = OpenAI(api_key=settings.JUDGE_OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL, max_retries=2, timeout=90)
            self.model = settings.JUDGE_MODEL
            self.route = f"openai:{self.model} (JUDGE_OPENAI_API_KEY)"
        elif settings.JUDGE_GROQ:
            self._client = OpenAI(api_key=settings.JUDGE_GROQ, base_url=settings.GROQ_BASE_URL, max_retries=2, timeout=90)
            self.model, self._extra = GROQ_JUDGE_MODEL, {"reasoning_effort": "low"}
            self.route = f"groq:{self.model} (JUDGE_GROQ)"
        elif settings.llm_configured:
            self.route = "app gateway (no judge key set)"
        else:
            raise JudgeUnavailable("No judge LLM: set JUDGE_OPENAI_API_KEY (or OPENAI_API_KEY) in backend/.env")

    def ask(self, system: str, user: str) -> dict:
        """One JSON-mode call at temperature 0."""
        self.calls += 1
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        if self._client is not None:
            resp = self._client.chat.completions.create(  # type: ignore[attr-defined]
                model=self.model, messages=messages, temperature=0, max_completion_tokens=2048,
                response_format={"type": "json_object"}, **self._extra,
            )
            return parse_json(resp.choices[0].message.content or "{}")
        return parse_json(chat(messages, json_mode=True, temperature=0, feature="eval-judge", max_tokens=2048).text)
