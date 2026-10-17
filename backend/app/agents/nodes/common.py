import time
from contextlib import contextmanager


def client_text(messages: list[dict]) -> str:
    """Everything the client said, in order. Only these words count as stated facts."""
    return "\n\n".join(m["content"] for m in messages if m["role"] == "user")


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
