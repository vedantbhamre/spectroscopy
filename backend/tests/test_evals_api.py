"""The Evals page button: a run starts only on POST, one at a time, with a cooldown. No LLM calls here."""

import threading
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import app.evals_api as api


@pytest.fixture
def client(monkeypatch):
    from app.main import app

    monkeypatch.setattr(api, "_state", {**api._state, "running": False, "error": None})
    monkeypatch.setattr(api.settings, "GROQ_API_KEY", "g1")  # llm_configured
    return TestClient(app)


def test_status_never_starts_a_run(client, monkeypatch):
    started = []
    monkeypatch.setattr(api.threading, "Thread", lambda **kw: started.append(kw))
    body = client.get("/evals/status").json()
    assert not body["running"] and body["scenarios"] == 14 and started == []


def test_run_starts_once_and_blocks_while_running(client, monkeypatch):
    monkeypatch.setattr(api, "last_run_at", lambda: None)
    started, gate = [], threading.Event()
    monkeypatch.setattr(api, "_worker", lambda judge: (started.append(judge), gate.wait(5)))
    assert client.post("/evals/run", json={"judge": False}).json()["running"]
    assert client.post("/evals/run", json={}).status_code == 409
    gate.set()
    assert started == [False]


def test_cooldown_after_a_recent_run(client, monkeypatch):
    monkeypatch.setattr(api, "last_run_at", lambda: datetime.now(timezone.utc) - timedelta(minutes=1))
    monkeypatch.setattr(api.settings, "EVAL_COOLDOWN_MIN", 30)
    r = client.post("/evals/run", json={})
    assert r.status_code == 429 and r.json()["cooldown_s"] > 28 * 60
