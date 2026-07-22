import sys


def _check_python_version():
    if sys.version_info[:2] not in ((3, 10), (3, 11)):
        sys.exit(
            "run_agent.py requires Python 3.10 or 3.11 (SQLAlchemy/llama-index "
            "raise an AssertionError on 3.13+, see blueprint \xa73). "
            f"Current interpreter: {sys.version.split()[0]}"
        )


_check_python_version()

import argparse  # noqa: E402
import asyncio  # noqa: E402
import os  # noqa: E402

from agent.chat.config import Config  # noqa: E402
from agent.chat.manager import RAGAgent  # noqa: E402
from agent.crawler.base import WebCrawler  # noqa: E402


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


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--crawl",
        metavar="URL",
        default=None,
        help="Crawl this URL into config.INPUT_DIR before indexing (additive -- omit for unchanged behavior).",
    )
    return parser.parse_args()


def main():
    args = _parse_args()

    config = Config()
    config.validate(strict=True)

    if args.crawl:
        crawler = WebCrawler(args.crawl, output_dir=config.INPUT_DIR)
        crawl_result = asyncio.run(crawler.crawl_urls([args.crawl]))
        print(f"[run_agent] crawled {crawl_result['pages_written']} page(s) from {args.crawl!r} into {config.INPUT_DIR!r}")
        if crawl_result["skipped"]:
            print(f"[run_agent] skipped: {crawl_result['skipped']}")

    rag_agent = RAGAgent(config)
    key_name = config.NAMESPACE

    if args.crawl:
        chunk_count = len(rag_agent.document_handler.get_nodes())
        print(f"[run_agent] {chunk_count} chunk(s) parsed from {config.INPUT_DIR!r} (chunk_size={config.CHUNK_SIZE})")

    if _index_exists(config, key_name, rag_agent.index_manager):
        print(f"[run_agent] found existing index for key_name={key_name!r} -- loading.")
        rag_agent.index_manager.load_index(key_name)
    else:
        print(f"[run_agent] no existing index for key_name={key_name!r} -- creating.")
        rag_agent.index_manager.create_index(key_name)

    asyncio.run(_interactive_loop(rag_agent, key_name))


async def _interactive_loop(rag_agent, key_name):
    # One persistent event loop for the whole session, not one per query.
    # Ollama caches an async client bound to whatever loop is running when
    # it's first used (confirmed via inspect.signature: Ollama.__init__
    # takes/stores an async_client) -- calling asyncio.run() fresh per query
    # creates a new loop each time, and a second query then crashes with
    # "RuntimeError: Event loop is closed" trying to reuse the first loop's
    # client. Looping inside one asyncio.run() call (this function) and
    # awaiting RAGAgent.arun() directly avoids that entirely. This also lets
    # RAGAgent reuse its AgentManager (and the reranker's ~3s model load)
    # across queries instead of rebuilding it every time -- see
    # RAGAgent._get_agent_manager.
    print("[run_agent] entering interactive query loop -- blank line to quit.")
    while True:
        prompt = input("Enter your query: ")
        if not prompt.strip():
            break
        answer = await rag_agent.arun(prompt, key_name)
        print(answer)


if __name__ == "__main__":
    main()
