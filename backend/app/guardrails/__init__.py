"""The Safety Gate (section 2 of the architecture).

Public surface:
    build_guard()        -> a Guard with `.check(text) -> GuardResult`
    initialize_rails()   -> build the process-wide gate (8hr-MARATHON template interface)
    check(text)          -> GuardResult from the process-wide gate
    guard(text)          -> (fired, response), template interface: fired only for hard blocks
    GuardResult, GuardCategory

Mode is picked once at startup:
    LLM configured (OpenAI / Portkey) -> LLMGuard on the small model (gpt-4o-mini), RuleGuard as runtime fallback
    otherwise, or GUARD_MODE=rules  -> RuleGuard (no network)
Both implement the same interface, so callers never branch on the mode.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.guardrails.base import Guard, GuardCategory, GuardResult
from app.guardrails.rule_guard import RuleGuard

__all__ = ["build_guard", "initialize_rails", "check", "guard", "Guard", "GuardResult", "GuardCategory"]

_GUARD: Guard | None = None


def build_guard() -> Guard:
    """Select the Safety Gate implementation for this process."""
    if settings.llm_guard_available:
        try:
            from app.guardrails.llm_guard import LLMGuard

            return LLMGuard(fallback=RuleGuard())
        except Exception as exc:  # import failure -> degrade gracefully
            logging.getLogger("spectrasense.guard").warning("LLM guard unavailable (%s); using rule-based gate.", exc)
    return RuleGuard()


def initialize_rails() -> None:
    global _GUARD
    _GUARD = build_guard()


def check(text: str) -> GuardResult:
    if _GUARD is None:
        initialize_rails()
    return _GUARD.check(text)  # type: ignore[union-attr]


def guard(text: str) -> tuple[bool, str | None]:
    r = check(text)
    return (True, r.message) if not r.passed else (False, None)
