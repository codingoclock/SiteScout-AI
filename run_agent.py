import sys


def _check_python_version():
    if sys.version_info[:2] not in ((3, 10), (3, 11)):
        sys.exit(
            "run_agent.py requires Python 3.10 or 3.11 (SQLAlchemy/llama-index "
            "raise an AssertionError on 3.13+, see blueprint \xa73). "
            f"Current interpreter: {sys.version.split()[0]}"
        )


_check_python_version()

import os  # noqa: E402

from agent.chat.config import Config  # noqa: E402
from agent.chat.manager import RAGAgent  # noqa: E402


def _index_exists(config, key_name, index_manager):
    store_type = config.STORE_TYPE

    if store_type == "chromadb":
        vector_store = index_manager.index_backend.storage_context.vector_store
        return vector_store.client.count() > 0

    if store_type == "disk":
        return os.path.isdir(os.path.join(".", "storage", key_name))

    if store_type == "redis":
        return os.path.isfile(os.path.join(".", "storage", key_name, "redis_index_id.json"))

    if store_type == "mongodb":
        return os.path.isfile(os.path.join(".", "storage", key_name, "mongo_index_id.json"))

    raise ValueError(f"Unknown STORE_TYPE: {store_type!r}")


def main():
    config = Config()
    config.validate(strict=True)

    rag_agent = RAGAgent(config)
    key_name = config.NAMESPACE

    if _index_exists(config, key_name, rag_agent.index_manager):
        print(f"[run_agent] found existing index for key_name={key_name!r} -- loading.")
        rag_agent.index_manager.load_index(key_name)
    else:
        print(f"[run_agent] no existing index for key_name={key_name!r} -- creating.")
        rag_agent.index_manager.create_index(key_name)

    prompt = input("Enter your query: ")
    answer = rag_agent.run(prompt, key_name)
    print(answer)


if __name__ == "__main__":
    main()
