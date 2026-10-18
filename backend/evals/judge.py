"""Judge LLM for the evals.

Uses its own key on the active provider so grading never rate-limits the live app, as in the
8hr-MARATHON template: LLM_PROVIDER=groq → JUDGE_GROQ (JUDGE_GROQ_MODEL); openai →
JUDGE_OPENAI_API_KEY (JUDGE_MODEL, default gpt-4o-mini), else JUDGE_GROQ. Without a judge key
it falls back to the app's gateway, so the evals still run with one key; the report records
which route was used.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import settings
from app.gateway import chat, parse_json
from app.gateway.client import _extra


class JudgeUnavailable(RuntimeError):
    pass


@dataclass
class Judge:
    calls: int = 0
    route: str = field(default="")
    model: str = field(default="")
    _client: object | None = None

    def __post_init__(self) -> None:
        from openai import OpenAI

        openai_key = settings.JUDGE_OPENAI_API_KEY if settings.LLM_PROVIDER != "groq" else None
        if openai_key:
            self._client = OpenAI(api_key=openai_key, base_url=settings.OPENAI_BASE_URL, max_retries=2, timeout=90)
            self.model = settings.JUDGE_MODEL
            self.route = f"openai:{self.model} (JUDGE_OPENAI_API_KEY)"
        elif settings.JUDGE_GROQ:
            self._client = OpenAI(api_key=settings.JUDGE_GROQ, base_url=settings.GROQ_BASE_URL, max_retries=4, timeout=90)
            self.model = settings.JUDGE_GROQ_MODEL
            self.route = f"groq:{self.model} (JUDGE_GROQ)"
        elif settings.llm_configured:
            self.route = f"app gateway ({settings.LLM_PROVIDER}, no judge key set)"
        else:
            raise JudgeUnavailable("No judge LLM: set a judge key or an app LLM key in backend/.env")

    def ask(self, system: str, user: str) -> dict:
        """One JSON-mode call at temperature 0."""
        self.calls += 1
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        if self._client is not None:
            resp = self._client.chat.completions.create(  # type: ignore[attr-defined]
                model=self.model, messages=messages, temperature=0, max_completion_tokens=2048,
                response_format={"type": "json_object"}, **_extra(self.model),
            )
            return parse_json(resp.choices[0].message.content or "{}")
        return parse_json(chat(messages, json_mode=True, temperature=0, feature="eval-judge", max_tokens=2048, tier="small").text)
