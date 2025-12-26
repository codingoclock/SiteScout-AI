import os
from dotenv import load_dotenv

# Load environment variables from .env (must be present in deployment)
load_dotenv()


class Config:
    """Environment-backed configuration for SiteScoutAI.

    All secrets and runtime configuration must come from environment
    variables (e.g., a .env file). This class intentionally uses a
    zero-argument constructor and provides a `validate()` method so the
    application can fail fast with clear errors.
    """

    def __init__(self):
        # -------- LLM --------
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.MODEL_TYPE = (os.getenv("MODEL_TYPE") or "openai").lower()
        # Allow either explicit OPENAI_MODEL or generic MODEL env var
        self.MODEL = os.getenv("OPENAI_MODEL") or os.getenv("MODEL") or "gpt-3.5-turbo"

        # Ollama / open-source LLMs
        self.OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
        self.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

        # -------- STORAGE --------
        self.store_type = (os.getenv("STORE_TYPE") or "redis").lower()
        self.STORE_HOST = os.getenv("STORE_HOST", "localhost")
        try:
            self.STORE_PORT = int(os.getenv("STORE_PORT", 6379))
        except (TypeError, ValueError):
            self.STORE_PORT = 6379

        self.CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

        # -------- MONGODB --------
        self.URI = os.getenv("MONGODB_URI")
        self.NAMESPACE = os.getenv("NAMESPACE") or os.getenv("MONGODB_DB") or "default"

        # -------- INPUT / INDEX --------
        # INPUT_FILES can be a comma-separated list in env, or a single path
        input_files = os.getenv("INPUT_FILES", "./data")
        self.INPUT_FILES = [p.strip() for p in input_files.split(",") if p.strip()]

        self.EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")

        # -------- RAG PARAMS (tunable) --------
        try:
            self.CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1024))
        except (TypeError, ValueError):
            self.CHUNK_SIZE = 1024

        try:
            self.TEMPERATURE = float(os.getenv("TEMPERATURE", 0))
        except (TypeError, ValueError):
            self.TEMPERATURE = 0.0

        self.persist_disk = os.getenv("PERSIST_DISK", "false").lower() in ("1", "true", "yes")

    def validate(self, strict: bool = True) -> None:
        """Validate required configuration values.

        - If `strict` is True, missing required secrets will raise RuntimeError.
        - If `strict` is False, missing values will only be logged.
        """
        errors = []

        if self.MODEL_TYPE == "openai" and not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required when MODEL_TYPE=openai")

        if self.MODEL_TYPE in ("open_source", "ollama") and not (self.OLLAMA_BASE_URL or self.OLLAMA_MODEL):
            errors.append("OLLAMA_BASE_URL or OLLAMA_MODEL should be set for open_source/ollama MODEL_TYPE")

        if self.store_type == "mongodb" and not (self.URI or (self.STORE_HOST and self.STORE_PORT)):
            errors.append("MONGODB_URI or STORE_HOST/STORE_PORT must be set for mongodb STORE_TYPE")

        if errors:
            msg = "Configuration validation failed: " + "; ".join(errors)
            if strict:
                raise RuntimeError(msg)
            else:
                # Defer to caller if non-strict
                import logging

                logging.warning(msg)

    def as_dict(self):
        """Return the config as a dict (helpful for debugging)."""
        return {
            "MODEL_TYPE": self.MODEL_TYPE,
            "MODEL": self.MODEL,
            "OPENAI_API_KEY": bool(self.OPENAI_API_KEY),
            "OLLAMA_BASE_URL": self.OLLAMA_BASE_URL,
            "OLLAMA_MODEL": self.OLLAMA_MODEL,
            "store_type": self.store_type,
            "STORE_HOST": self.STORE_HOST,
            "STORE_PORT": self.STORE_PORT,
            "CHROMA_PERSIST_DIR": self.CHROMA_PERSIST_DIR,
            "URI": self.URI,
            "NAMESPACE": self.NAMESPACE,
            "INPUT_FILES": self.INPUT_FILES,
            "EMBEDDING_MODEL": self.EMBEDDING_MODEL,
            "CHUNK_SIZE": self.CHUNK_SIZE,
            "TEMPERATURE": self.TEMPERATURE,
            "persist_disk": self.persist_disk,
        }
