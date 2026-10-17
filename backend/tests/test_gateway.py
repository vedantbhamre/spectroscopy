from app.config import settings
from app.gateway import client


def test_fallback_order_uses_both_keys(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "k1")
    monkeypatch.setattr(settings, "OPENAI_FALLBACK_API_KEY", "k2")
    monkeypatch.setattr(settings, "PRIMARY_MODEL", "gpt-4o")
    monkeypatch.setattr(settings, "FALLBACK_MODEL", "gpt-4o-mini")
    assert [(k, m) for k, m, _ in client.attempts()] == [("k1", "gpt-4o"), ("k2", "gpt-4o"), ("k1", "gpt-4o-mini"), ("k2", "gpt-4o-mini")]
    assert [m for _, m, _ in client.attempts("small")][:2] == ["gpt-4o-mini", "gpt-4o-mini"]


def test_fallback_key_alone_is_enough(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_FALLBACK_API_KEY", "k2")
    monkeypatch.setattr(settings, "PORTKEY_API_KEY", None)
    assert settings.llm_configured
    assert {k for k, _, _ in client.attempts()} == {"k2"}


def test_chat_moves_to_fallback_key_on_error(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "k1")
    monkeypatch.setattr(settings, "OPENAI_FALLBACK_API_KEY", "k2")
    monkeypatch.setattr(settings, "PORTKEY_API_KEY", None)
    calls = []

    class Fake:
        def __init__(self, key):
            self.key = key
            self.chat = self
            self.completions = self

        def create(self, model, **kw):
            calls.append((self.key, model))
            assert "max_completion_tokens" in kw
            if self.key == "k1":
                raise RuntimeError("429 quota exceeded")
            return type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": "ok"})()})()]})()

    monkeypatch.setattr(client, "_openai_client", Fake)
    res = client.chat([{"role": "user", "content": "hi"}])
    assert res.text == "ok" and res.via == "openai-fallback-key"
    assert calls == [("k1", settings.PRIMARY_MODEL), ("k2", settings.PRIMARY_MODEL)]
