import pytest

from app.config import settings
from app.gateway import client


@pytest.fixture
def keys(monkeypatch):
    """OpenAI k1/k2 and Groq g1/g2 configured; no Portkey, no fallback provider."""
    for name, value in {"OPENAI_API_KEY": "k1", "OPENAI_FALLBACK_API_KEY": "k2", "GROQ_API_KEY": "g1", "GROQ_FALLBACK_API_KEY": "g2",
                        "OPENAI_MODEL": "gpt-4o", "OPENAI_SMALL_MODEL": "gpt-4o-mini", "GROQ_MODEL": "big", "GROQ_SMALL_MODEL": "small",
                        "PORTKEY_API_KEY": None, "LLM_FALLBACK_PROVIDER": ""}.items():
        monkeypatch.setattr(settings, name, value)
    return monkeypatch


def pairs(tier="default"):
    return [(k, m) for k, m, _, _ in client.attempts(tier)]


def test_openai_order_uses_both_keys(keys):
    keys.setattr(settings, "LLM_PROVIDER", "openai")
    assert pairs() == [("k1", "gpt-4o"), ("k2", "gpt-4o"), ("k1", "gpt-4o-mini"), ("k2", "gpt-4o-mini")]
    assert [m for _, m in pairs("small")][:2] == ["gpt-4o-mini", "gpt-4o-mini"]
    assert settings.PRIMARY_MODEL == "gpt-4o"


def test_groq_provider_never_touches_openai(keys):
    keys.setattr(settings, "LLM_PROVIDER", "groq")
    assert pairs() == [("g1", "big"), ("g2", "big"), ("g1", "small"), ("g2", "small")]
    assert {base for *_, base in client.attempts()} == {settings.GROQ_BASE_URL}
    assert settings.PRIMARY_MODEL == "big" and settings.FALLBACK_MODEL == "small"


def test_fallback_provider_is_opt_in(keys):
    keys.setattr(settings, "LLM_PROVIDER", "groq")
    keys.setattr(settings, "LLM_FALLBACK_PROVIDER", "openai")
    labels = [label for _, _, label, _ in client.attempts()]
    assert labels[:4] == ["groq", "groq-fallback-key"] * 2 and labels[4:] == ["openai", "openai-fallback-key"] * 2


def test_fallback_key_alone_is_enough(keys):
    keys.setattr(settings, "LLM_PROVIDER", "openai")
    keys.setattr(settings, "OPENAI_API_KEY", None)
    assert settings.llm_configured
    assert {k for k, _ in pairs()} == {"k2"}


def test_reasoning_effort_only_for_reasoning_models():
    assert client._extra("openai/gpt-oss-120b") == {"reasoning_effort": "low"}
    assert client._extra("llama-3.3-70b-versatile") == {} and client._extra("gpt-4o") == {}


def test_chat_moves_to_fallback_key_on_error(keys):
    keys.setattr(settings, "LLM_PROVIDER", "openai")
    calls = []

    class Fake:
        def __init__(self, key, base_url):
            self.key = key
            self.chat = self
            self.completions = self

        def create(self, model, **kw):
            calls.append((self.key, model))
            assert "max_completion_tokens" in kw
            if self.key == "k1":
                raise RuntimeError("429 quota exceeded")
            return type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": "ok"})()})()]})()

    keys.setattr(client, "_openai_client", Fake)
    res = client.chat([{"role": "user", "content": "hi"}])
    assert res.text == "ok" and res.via == "openai-fallback-key"
    assert calls == [("k1", "gpt-4o"), ("k2", "gpt-4o")]


def test_json_mode_rejection_retries_without_json_mode(keys):
    keys.setattr(settings, "LLM_PROVIDER", "groq")
    calls = []

    class Fake:
        def __init__(self, key, base_url):
            self.chat = self
            self.completions = self

        def create(self, model, **kw):
            calls.append("response_format" in kw)
            if "response_format" in kw:
                raise RuntimeError("Error code: 400 - Failed to generate JSON. Please adjust your prompt.")
            return type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": '{"ok": 1}'})()})()]})()

    keys.setattr(client, "_openai_client", Fake)
    assert client.chat([{"role": "user", "content": "hi"}], json_mode=True).text == '{"ok": 1}'
    assert calls == [True, False]
