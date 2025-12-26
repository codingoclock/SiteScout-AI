"""
Minimal, production-ready RAG agent entry script for SiteScoutAI.

Usage:
    python run_agent.py

Features:
- Loads configuration from environment variables with reasonable defaults
- Initializes logging using the project's Logger utility
- Creates and initializes a RAGAgent (storage + index + LLM)
- Loads an existing index (or offers to create one from provided input files)
- Accepts a single user query from input() and prints the response
- Structured so it can be extended into a FastAPI app (functions are modular)

Notes:
- This script uses only the project's modules (no external reimplementation).
- It assumes environment variables are already set (or defaults are acceptable).
"""

import os
import sys
import asyncio
import logging
from typing import Optional

# Ensure project root is on path so local imports work when running the script
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Prefer direct module imports from the local package to avoid relying on an
# installed package name. These are the project's lightweight utilities.
from agent.chat.config import Config
from agent.chat.logger import Logger
# NOTE: Heavy imports (llama_index, sqlalchemy) are deferred until runtime when
# the RAG agent is actually instantiated to provide clearer error messages.


def check_python_compatibility() -> bool:
    """Ensure the running Python version is supported by the dependencies.

    LlamaIndex currently pulls in SQLAlchemy which is incompatible with
    Python >= 3.12 in older versions. We must detect the interpreter version
    early and exit gracefully to avoid obscure import errors.

    Returns True if compatible, False otherwise.
    """
    major = sys.version_info.major
    minor = sys.version_info.minor
    logging.debug("Detected Python version: %s.%s", major, minor)

    if major > 3 or (major == 3 and minor >= 12):
        # Do not import llama_index or any heavy dependency — just log and exit.
        logging.error(
            "Incompatible Python version detected: %s.%s. "
            "This project supports Python 3.10 and 3.11. "
            "Please use a compatible interpreter (e.g., pyenv/venv) and try again.",
            major,
            minor,
        )
        return False
    return True


def load_config_from_env() -> Config:
    """Return a Config instance that reads settings from the environment (.env).

    Centralizing environment parsing in Config() ensures all secrets come from
    the .env and avoids duplicating env parsing logic.
    """
    return Config()


async def ask_agent(rag, query: str, key_name: str) -> str:
    """Send a query to the RAG agent and return the text response."""
    return await rag.run(query, key_name)


def ensure_index(rag, key_name: str) -> None:
    """Try to load an index; if missing, prompt the user to create one from documents."""
    try:
        # Attempt to load an existing index
        index = None
        try:
            index = rag.index_manager.load_index(key_name)
        except Exception:
            # Some backends may raise on load; treat as no-index
            index = None

        if index:
            logging.info("Index loaded for key: %s", key_name)
            return

        # No index found — ask user whether to create one from local files
        resp = input(
            f"No index found for '{key_name}'. Create index now from files at '{rag.config.INPUT_FILES}'? [y/N]: "
        ).strip().lower()
        if resp == "y":
            logging.info("Creating index for key: %s", key_name)
            rag.create_index(key_name)
            logging.info("Index created and stored for key: %s", key_name)
        else:
            logging.warning("No index available. The agent may not be able to answer content questions.")
    except Exception as exc:
        logging.exception("Error while ensuring index: %s", exc)


def create_rag_agent(config):
    """Lazily import and instantiate the RAGAgent.

    This defers heavy imports (like llama_index and SQLAlchemy) until after
    we've validated the Python version. It also provides clearer error
    messages when imports fail due to package incompatibilities.
    """
    try:
        from agent.chat.manager import RAGAgent
    except Exception as exc:
        logging.exception("Failed to import RAGAgent; likely a dependency compatibility issue: %s", exc)
        logging.error("If this is due to SQLAlchemy / Python incompatibility, ensure Python 3.10 or 3.11 is used and the appropriate package versions are installed.")
        logging.error("For debugging, run: python -c 'import platform, sqlalchemy; print(platform.python_version(), sqlalchemy.__version__)'")
        raise

    return RAGAgent(config)


def main() -> None:
    """Top-level entrypoint for running the RAG agent from the command-line.

    This function performs a Python version compatibility check before
    importing heavy dependencies (transitively pulled in by LlamaIndex).
    It logs structured runtime choices and initializes the RAG agent lazily.
    """

    # Setup logging using provided utility
    Logger.setup()
    logging.info("Starting SiteScoutAI RAG agent")

    # Load configuration
    config = load_config_from_env()

    # Validate configuration (fails fast with helpful error messages)
    try:
        config.validate(strict=True)
    except RuntimeError as e:
        logging.error("Configuration validation failed: %s", e)
        sys.exit(2)

    logging.info("Effective configuration: %s", config.as_dict())

    # Ensure interpreter is compatible before importing llama_index/SQLAlchemy
    if not check_python_compatibility():
        # Exit with non-zero code so automation knows this is a compatibility failure
        sys.exit(1)

    # Structured logging for user visibility and diagnostics
    logging.info("Runtime information:")
    logging.info("  Python version: %s", ".".join(map(str, sys.version_info[:3])))
    logging.info("  LLM provider: %s", config.MODEL_TYPE)
    logging.info("  LLM model: %s", config.MODEL)
    logging.info("  Storage backend: %s", config.store_type)
    logging.info("  Namespace / key: %s", config.NAMESPACE)

    # If using OpenAI provider, ensure API key is available (but allow Ollama/open_source without it)
    if config.MODEL_TYPE and config.MODEL_TYPE.lower() == "openai" and not config.OPENAI_API_KEY:
        logging.warning("OPENAI_API_KEY not set, but MODEL_TYPE=openai — OpenAI LLM calls will fail without a valid API key.")
    elif not config.OPENAI_API_KEY:
        logging.info("No OpenAI API key provided. If you are using an open-source LLM (e.g., Ollama) this is expected and fine.")

    # Lazily create the RAGAgent (this will run heavy imports inside the helper)
    try:
        rag = create_rag_agent(config)
    except Exception:
        logging.error("Unable to initialize the RAG agent due to import or dependency issues.")
        return

    key_name = config.NAMESPACE or "default"

    # Ensure index is available (load or create)
    ensure_index(rag, key_name)

    try:
        query = input("Enter your question (single-line): ").strip()
        if not query:
            logging.info("No query provided. Exiting.")
            return

        logging.info("Query received — sending to agent...")

        # Run the agent asynchronously and print the response
        response = asyncio.run(ask_agent(rag, query, key_name))

        print("\n--- Agent response ---")
        print(response)
        print("--- End response ---\n")

    except KeyboardInterrupt:
        logging.info("Aborted by user")
    except Exception as exc:
        logging.exception("Error while running agent: %s", exc)


if __name__ == "__main__":
    main()
