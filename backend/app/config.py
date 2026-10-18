import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    return value if value not in ("", None) else default


class Settings:
    # --- LLM provider: "groq" | "openai". Each has a primary and a fallback key, a large and a small model. ---
    LLM_PROVIDER = (_env("LLM_PROVIDER", "openai") or "openai").lower()
    # Other provider tried after every attempt on the active one fails. Empty = none, so testing on
    # one provider never spends credits on the other.
    LLM_FALLBACK_PROVIDER = (_env("LLM_FALLBACK_PROVIDER", "") or "").lower()

    OPENAI_API_KEY = _env("OPENAI_API_KEY")
    OPENAI_FALLBACK_API_KEY = _env("OPENAI_FALLBACK_API_KEY")  # used when the primary key fails (quota, rate limit)
    # Always explicit: an empty OPENAI_BASE_URL= line in .env would otherwise reach the SDK as base URL ""
    OPENAI_BASE_URL = _env("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL = _env("OPENAI_MODEL", "gpt-4o")
    OPENAI_SMALL_MODEL = _env("OPENAI_FALLBACK_MODEL", "gpt-4o-mini")

    GROQ_API_KEY = _env("GROQ_API_KEY")
    GROQ_FALLBACK_API_KEY = _env("GROQ_FALLBACK_API_KEY")
    GROQ_BASE_URL = "https://api.groq.com/openai/v1"
    GROQ_MODEL = _env("GROQ_MODEL", "openai/gpt-oss-120b")
    GROQ_SMALL_MODEL = _env("GROQ_SMALL_MODEL", "openai/gpt-oss-20b")

    PORTKEY_API_KEY = _env("PORTKEY_API_KEY")
    PORTKEY_SLUG = _env("PORTKEY_SLUG", "openai")  # Portkey integration holding the primary key
    PORTKEY_SLUG_2 = _env("PORTKEY_SLUG_2", "openai-fallback")  # integration holding the fallback key

    # Retrieved chunks sent to the responder: the main driver of input tokens per assessment.
    RETRIEVE_TOP_N = int(_env("RETRIEVE_TOP_N", "8") or 8)  # distinct pages; 8 measured best (recall did not rise at 10)
    RERANK = (_env("RERANK", "off") or "off").lower()  # "flashrank" to reorder the keyword hits (measured no gain)

    @property
    def PRIMARY_MODEL(self) -> str:
        return self.GROQ_MODEL if self.LLM_PROVIDER == "groq" else self.OPENAI_MODEL

    @property
    def FALLBACK_MODEL(self) -> str:
        return self.GROQ_SMALL_MODEL if self.LLM_PROVIDER == "groq" else self.OPENAI_SMALL_MODEL

    # --- Embeddings: "local" (BGE-base on CPU, default, measured), "gemini" (Qdrant index built by ingestion), "off" ---
    EMBEDDINGS = (_env("EMBEDDINGS", "local") or "local").lower()
    LOCAL_EMBEDDING_MODEL = _env("LOCAL_EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")
    EMBEDDING_CACHE_DIR = BACKEND_DIR / ".embeddings"
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

    # --- Evals: separate key for the judge LLM, on the active provider; else the app gateway ---
    JUDGE_OPENAI_API_KEY = _env("JUDGE_OPENAI_API_KEY")
    JUDGE_MODEL = _env("JUDGE_MODEL", "gpt-4o-mini")  # mini: ~16x cheaper than gpt-4o, fine for 0/1 grading
    JUDGE_GROQ = _env("JUDGE_GROQ")
    JUDGE_GROQ_MODEL = _env("JUDGE_GROQ_MODEL", "openai/gpt-oss-120b")
    # The Evals page's "Run evals" button: minimum minutes between runs (latest run time is on disk).
    EVAL_COOLDOWN_MIN = float(_env("EVAL_COOLDOWN_MIN", "30") or 30)

    @property
    def llm_configured(self) -> bool:
        return bool(self.PORTKEY_API_KEY or self.OPENAI_API_KEY or self.OPENAI_FALLBACK_API_KEY
                    or self.GROQ_API_KEY or self.GROQ_FALLBACK_API_KEY)

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
