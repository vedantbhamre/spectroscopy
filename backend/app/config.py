import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    return value if value not in ("", None) else default


class Settings:
    # --- LLM: OpenAI (optionally via Portkey) ---
    OPENAI_API_KEY = _env("OPENAI_API_KEY")
    OPENAI_FALLBACK_API_KEY = _env("OPENAI_FALLBACK_API_KEY")  # used when the primary key fails (quota, rate limit)
    # Always explicit: an empty OPENAI_BASE_URL= line in .env would otherwise reach the SDK as base URL ""
    OPENAI_BASE_URL = _env("OPENAI_BASE_URL", "https://api.openai.com/v1")
    PRIMARY_MODEL = _env("OPENAI_MODEL", "gpt-4o")
    FALLBACK_MODEL = _env("OPENAI_FALLBACK_MODEL", "gpt-4o-mini")
    PORTKEY_API_KEY = _env("PORTKEY_API_KEY")
    PORTKEY_SLUG = _env("PORTKEY_SLUG", "openai")  # Portkey integration holding the primary OpenAI key
    PORTKEY_SLUG_2 = _env("PORTKEY_SLUG_2", "openai-fallback")  # integration holding the fallback key
    # Last-resort provider when every OpenAI attempt fails (outage, quota): Groq's OpenAI-compatible API
    GROQ_FALLBACK_API_KEY = _env("GROQ_FALLBACK_API_KEY", _env("GROQ_API_KEY"))
    GROQ_BASE_URL = "https://api.groq.com/openai/v1"
    GROQ_MODEL = _env("GROQ_MODEL", "openai/gpt-oss-120b")
    GROQ_SMALL_MODEL = _env("GROQ_SMALL_MODEL", "openai/gpt-oss-20b")

    # --- Embeddings ---
    GEMINI_API_KEY = _env("GEMINI_API_KEY")
    EMBEDDING_MODEL = "models/gemini-embedding-2-preview"
    EMBEDDING_DIM = 3072

    # --- Vector DB ---
    QDRANT_URL = _env("QDRANT_CLUSTER_ENDPOINT")
    QDRANT_API_KEY = _env("QDRANT_API_KEY")
    QDRANT_COLLECTION = _env("QDRANT_COLLECTION", "afs_spectroscopy")
    QDRANT_LOCAL_PATH = str(BACKEND_DIR / ".qdrant")

    # --- Knowledge base ---
    PROCESSED_DIR = BACKEND_DIR / "processed_data"
    PAGES_FILE = PROCESSED_DIR / "pages.json"
    CHUNKS_FILE = PROCESSED_DIR / "chunks.json"
    MATERIALS_DIR = Path(_env("MATERIALS_DIR", str(BACKEND_DIR / "data" / "materials"))).expanduser()

    # --- Observability ---
    LOGFIRE_TOKEN = _env("LOGFIRE_TOKEN")
    LANGSMITH_TRACING = _env("LANGSMITH_TRACING", "false")
    LANGSMITH_API_KEY = _env("LANGSMITH_API_KEY")
    LANGSMITH_ENDPOINT = _env("LANGSMITH_ENDPOINT")  # EU workspaces: https://eu.api.smith.langchain.com
    LANGSMITH_PROJECT = _env("LANGSMITH_PROJECT", "spectrasense")

    FRONTEND_ORIGIN = _env("FRONTEND_ORIGIN", "http://localhost:3000")

    # --- Safety gate: "llm" (small-model classifier, rules as fallback) | "rules" | unset = llm when an LLM is configured ---
    GUARD_MODE = _env("GUARD_MODE")

    # --- Evals: separate key for the judge LLM (OpenAI preferred, Groq accepted; else the app gateway) ---
    JUDGE_OPENAI_API_KEY = _env("JUDGE_OPENAI_API_KEY")
    JUDGE_MODEL = _env("JUDGE_MODEL", "gpt-4o")
    JUDGE_GROQ = _env("JUDGE_GROQ")

    @property
    def llm_configured(self) -> bool:
        return bool(self.PORTKEY_API_KEY or self.OPENAI_API_KEY or self.OPENAI_FALLBACK_API_KEY or self.GROQ_FALLBACK_API_KEY)

    @property
    def llm_guard_available(self) -> bool:
        if self.GUARD_MODE == "rules":
            return False
        return self.llm_configured


settings = Settings()

# LangSmith picks these up for automatic LangGraph tracing.
if settings.LANGSMITH_API_KEY:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", settings.LANGSMITH_TRACING or "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.LANGSMITH_API_KEY)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.LANGSMITH_PROJECT or "spectrasense")
    if settings.LANGSMITH_ENDPOINT:
        os.environ.setdefault("LANGCHAIN_ENDPOINT", settings.LANGSMITH_ENDPOINT)
