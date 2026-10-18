import re
import time
from contextlib import contextmanager


def client_text(messages: list[dict]) -> str:
    """Everything the client said, in order. Only these words count as stated facts."""
    return "\n\n".join(m["content"] for m in messages if m["role"] == "user")


_ECHO = re.compile(r"^\s*(?:-\s*)?Q:.*$|^\s*Answers to your questions:\s*$", re.I | re.M)
_A_PREFIX = re.compile(r"^\s*A:\s*", re.M)


def customer_words(text: str) -> str:
    """The customer's own words in a message: the UI repeats each question ("- Q: ...") above its answer ("A: ..."),
    and question wording must never become a customer fact."""
    return _A_PREFIX.sub("", _ECHO.sub("", text or "")).strip()


def client_turns(messages: list[dict]) -> list[str]:
    """The client's messages in order; turn 1 is the enquiry."""
    return [m["content"] for m in messages if m["role"] == "user"]


def transcript(messages: list[dict], limit: int = 12) -> str:
    rows = messages[-limit:]
    return "\n\n".join(f"{'Client' if m['role'] == 'user' else 'Assistant'}: {m['content']}" for m in rows)


@contextmanager
def step(state: dict, name: str):
    """Time a pipeline step and append it to the trace. Set rec['status'] / rec['detail'] inside."""
    rec = {"step": name, "status": "ok"}
    start = time.perf_counter()
    try:
        yield rec
    except Exception as e:
        rec.update(status="fail", detail=str(e)[:200])
        raise
    finally:
        rec["ms"] = round((time.perf_counter() - start) * 1000)
        state.setdefault("trace", []).append(rec)
