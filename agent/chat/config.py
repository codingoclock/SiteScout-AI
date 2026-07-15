# Config is the single source of truth for environment variables.
# Nothing outside this class should ever call os.getenv(...) directly —
# every other module must read settings through a Config instance.

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self):
        self.MODEL_TYPE = os.getenv("MODEL_TYPE", "openai")
        self.MODEL = os.getenv("OPENAI_MODEL") or os.getenv("MODEL") or "gpt-3.5-turbo"
        self.STORE_TYPE = os.getenv("STORE_TYPE", "redis")
        self.STORE_HOST = os.getenv("STORE_HOST", "localhost")
        self.STORE_PORT = self._int_env("STORE_PORT", 6379)
        self.NAMESPACE = os.getenv("NAMESPACE", "default")
        self.INPUT_DIR = os.getenv("INPUT_DIR", "./data")
        self.CHUNK_SIZE = self._int_env("CHUNK_SIZE", 1024)

    @staticmethod
    def _int_env(name, default):
        raw = os.getenv(name)
        if raw is None:
            return default
        if raw == "":
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def validate(self, strict=True):
        required = {
            "MODEL_TYPE": self.MODEL_TYPE,
            "MODEL": self.MODEL,
            "STORE_TYPE": self.STORE_TYPE,
            "STORE_HOST": self.STORE_HOST,
            "STORE_PORT": self.STORE_PORT,
            "NAMESPACE": self.NAMESPACE,
            "INPUT_DIR": self.INPUT_DIR,
            "CHUNK_SIZE": self.CHUNK_SIZE,
        }
        missing = [name for name, value in required.items() if value in (None, "")]

        if missing and strict:
            raise RuntimeError(
                "Missing required configuration values: " + ", ".join(missing)
            )

        return missing

    def as_dict(self):
        return {
            "MODEL_TYPE": self.MODEL_TYPE,
            "MODEL": self.MODEL,
            "STORE_TYPE": self.STORE_TYPE,
            "STORE_HOST": self.STORE_HOST,
            "STORE_PORT": self.STORE_PORT,
            "NAMESPACE": self.NAMESPACE,
            "INPUT_DIR": self.INPUT_DIR,
            "CHUNK_SIZE": self.CHUNK_SIZE,
        }
