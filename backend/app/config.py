import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    return value if value not in ("", None) else default


class Settings:
    # --- LLM gateway (Portkey → Groq) ---
    PORTKEY_API_KEY = _env("PORTKEY_API_KEY")
    GROQ_SLUG = _env("GROQ_SLUG", "rag")
    GROQ_SLUG_2 = _env("GROQ_SLUG_2", "brag")
    GROQ_API_KEY = _env("GROQ_API_KEY")
    GROQ_FALLBACK_API_KEY = _env("GROQ_FALLBACK_API_KEY")
    PRIMARY_MODEL = "llama-3.3-70b-versatile"
    FALLBACK_MODEL = "llama-3.1-8b-instant"

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
    LANGSMITH_PROJECT = _env("LANGSMITH_PROJECT", "spectrasense")

    FRONTEND_ORIGIN = _env("FRONTEND_ORIGIN", "http://localhost:3000")

    # --- Safety gate: "llm" (Groq 8B classifier, rules as fallback) | "rules" | unset = llm when an LLM is configured ---
    GUARD_MODE = _env("GUARD_MODE")

    # --- Evals: separate Groq key for the judge LLM (falls back to the app gateway) ---
    JUDGE_GROQ = _env("JUDGE_GROQ")

    @property
    def llm_configured(self) -> bool:
        return bool(self.PORTKEY_API_KEY or self.GROQ_API_KEY)

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
