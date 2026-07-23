# SiteScout AI

A local-first **Agentic RAG** (Retrieval-Augmented Generation) system:
crawl a web page, index its content, and ask questions about it through an
LLM-driven agent that *decides* whether and when to retrieve grounded
context before answering, rather than retrieving on every question as a
fixed pipeline step. Built to run entirely on local models (Ollama), with
no cloud API key or network dependency required at query time -- an
OpenAI-backed path also exists in the code as a configuration option.

## Architecture

The pipeline is a straight line, each stage owned by one module:

```
crawl (agent/crawler/)
  -> parse & chunk (agent/chat/parsing.py)
  -> embed & store (agent/chat/storage.py, index.py)
  -> retrieve (hybrid: vector similarity + BM25, fused via RRF)
  -> rerank (cross-encoder, narrows to top-k)
  -> generate (LLM agent, tool-calling)
```

### Why this is Agentic RAG, specifically

The retrieve/rerank stages above aren't wired in as a fixed step that runs
on every question. They're wrapped into a single `QueryEngineTool`
(`knowledge_base`), handed to an LLM agent (`ReActAgent`, or `FunctionAgent`
for the OpenAI path) that decides, per question, whether to call it --
the same pattern used by tool-calling agent frameworks generally, applied
here with exactly one tool. That's the actual distinction between plain
RAG and Agentic RAG: retrieval as a tool an agent chooses to invoke, versus
retrieval as an unconditional pipeline stage.

This was verified empirically, not just designed this way in theory:
testing the same 5 questions against the same index showed tool-invocation
rates that varied by agent/prompt configuration (as low as 1/5, as high as
5/5) -- that variation only exists because the model is genuinely
*deciding* whether to retrieve, not executing a hardcoded step. Verbose
runs also showed genuine multi-step ReAct loops (Thought -> Action ->
Observation -> Thought -> Answer), sometimes 2-3 sequential LLM calls for
a single question, rather than one fixed retrieve-then-generate pass.

Scope, precisely -- what this is *not*: a single-tool agent (one
`knowledge_base` tool, not several capabilities to choose between), no
multi-agent orchestration or agent-to-agent handoff, no agentic query
decomposition (`QueryFusionRetriever` supports LLM-generated query
rewrites, but `num_queries` is deliberately set to `1` to avoid an extra
LLM round trip per query), and no verified conversational memory across
separate questions in a session (the CLI reuses the same agent setup
across queries for performance, but each query is still an independent
`agent.run()` call).

### Crawling (`agent/crawler/`)
- `url_manager.py` -- URL normalization (resolves relative links, strips
  fragments, dedupes trailing slashes) and a content-type filter (rejects
  images/archives/static assets).
- `sitemeta.py` -- `RobotsHandler` (respects `robots.txt` disallow rules)
  and `SitemapCrawler` (parses `sitemap.xml`, follows nested sitemap
  indexes, not just flat lists).
- `config.py` -- wraps crawl4ai's browser/crawl configuration, including a
  tuned `PruningContentFilter` that strips nav/footer/boilerplate out of
  the extracted markdown before it's written to disk.
- `base.py` -- `WebCrawler`: `crawl_urls()` for a specific list of pages
  (what `--crawl <url>` uses), `get_data()` for a bounded sitemap-first/
  BFS-fallback site crawl, both with a semaphore-bounded concurrency limit
  for politeness. Writes one markdown file per page into `INPUT_DIR`.

### RAG core (`agent/chat/`)
- `config.py` -- `Config`, the single source of truth for every setting
  (reads env vars once; nothing else in the codebase calls `os.getenv`
  directly). `validate(strict=True)` raises one error listing every
  missing value, not just the first.
- `parsing.py` -- `DocumentHandler`: loads files from `INPUT_DIR`, splits
  them into chunks (`CHUNK_SIZE`).
- `storage.py` / `index.py` -- factory-based, four interchangeable
  backends selected by `STORE_TYPE`: `chromadb` (in-memory, default,
  needs nothing else running), `disk` (persists to `./storage/<namespace>`),
  `redis`, `mongodb` (both need a running server, see Configuration below).
  Every storage class shares the exact same constructor signature so the
  factory can swap them without special-casing.
- `llm.py` -- `LLMManager`: `MODEL_TYPE=openai` (real OpenAI API, needs
  `OPENAI_API_KEY`) or `MODEL_TYPE=open_source` (local Ollama LLM +
  HuggingFace embeddings).
- `manager.py` -- `AgentManager`/`RAGAgent`: wraps the index in a
  `QueryEngineTool`. Retrieval is hybrid -- a vector similarity search and
  a BM25 keyword search each independently produce a candidate pool
  (`CANDIDATE_POOL_SIZE = 10`), fused into one ranked list via Reciprocal
  Rank Fusion (`QueryFusionRetriever`). That fused pool is then reranked
  down to `RERANK_TOP_K = 3` with a local cross-encoder
  (`cross-encoder/ms-marco-MiniLM-L-6-v2`, via `sentence-transformers`, no
  cloud call) before handing it to the agent. Picks `FunctionAgent` for
  `MODEL_TYPE=openai` or `ReActAgent` otherwise.

### Entry point (`run_agent.py`)
- Guards on Python 3.10/3.11 (llama-index has a known incompatibility on
  3.13+ on this stack).
- Loads and validates `Config`.
- Optional `--crawl <url>` flag: crawls that one page into `INPUT_DIR`
  before indexing.
- Checks whether an index already exists for the configured backend +
  namespace; loads it if so, creates it if not.
- Drops into an interactive loop: type a question, get an answer, repeat;
  blank line to quit.

## Features

- **Four interchangeable storage backends, switchable with a single
  config value.** No code changes, no re-implementation per backend --
  just set `STORE_TYPE` and go:
  - `STORE_TYPE=chromadb` -- in-memory, zero setup, the default for
    quick local use.
  - `STORE_TYPE=disk` -- persists to `./storage/<namespace>`, survives
    a restart.
  - `STORE_TYPE=redis` -- backed by a running Redis instance.
  - `STORE_TYPE=mongodb` -- backed by a running MongoDB instance.

  All four share one constructor contract, so the same `run_agent.py`
  flow works unmodified regardless of which one is active.

- **Hybrid search (vector + BM25) for better recall.** Retrieval doesn't
  rely on embedding similarity alone -- a BM25 keyword search runs
  alongside it, and the two candidate pools are combined with Reciprocal
  Rank Fusion (RRF), the standard technique for merging lexical and
  semantic search results. This catches cases pure vector search misses:
  an exact term, command, or name in the question that's a strong keyword
  match but not a strong semantic one. Verified directly, not assumed --
  on a real test page, a chunk containing the exact command `bundle exec`
  was ranked last (4th of 4) by vector similarity alone, and rose to 2nd
  once BM25 was fused in.

- **Reranking retrieval pipeline for higher-precision answers.** After
  hybrid retrieval casts its wide net (10 candidate chunks), a local
  cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) re-scores and
  narrows that pool down to the 3 chunks that are actually most relevant
  to the question -- catching genuinely relevant chunks that similarity
  scores alone tend to under-rank. This also shrinks the context the LLM
  has to read: instead of reasoning over the full unranked pool of 10, it
  only processes the top 3, which reduces generation time per query even
  though the reranking step itself adds a small, fixed cost.

- **Web crawler that behaves.** Respects `robots.txt` and sitemaps
  (including nested sitemap indexes, not just flat lists), filters out
  non-content URLs, crawls with bounded concurrency so it never hammers a
  site, and strips real navigation/boilerplate noise out of page content
  before indexing it.

- **Fully local, self-reliant operation.** The tested, working
  configuration runs entirely on local Ollama models on a single machine
  -- no API key, no billing, no internet dependency once the models are
  pulled. That makes it a practical, zero-cost research and study
  assistant: point it at a doc site, a paper, or a set of notes, and
  query it offline, which is particularly useful for students who want a
  RAG assistant without paying for cloud API access.

- **Session-aware CLI.** One process can answer multiple questions in a
  row without re-loading the reranker model or rebuilding the agent on
  every query -- a persistent session, not a one-shot script.

## Setup

### 1. Python version

Use Python 3.10 or 3.11 specifically -- `run_agent.py` enforces this and
will refuse to run on anything else (a known llama-index/SQLAlchemy issue
on 3.13+).

### 2. Virtual environment and dependencies

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -c constraints.txt -r requirements.txt
crawl4ai-setup   # one-time: fetches the Playwright browser binaries the crawler needs
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env` as needed -- see the Configuration reference below for every
variable. The important early decisions are `MODEL_TYPE` and `STORE_TYPE`.

### 4. Local models (recommended path: `MODEL_TYPE=open_source`)

Install [Ollama](https://ollama.com), then pull a small LLM and an
embedding model, e.g.:

```bash
ollama pull qwen3:1.7b
ollama pull qwen3-embedding:0.6b
```

Start the server. **On memory-constrained machines (8GB or less), cap it
to one resident model at a time** -- an LLM and an embedding model loaded
simultaneously can exceed available RAM and crash:

```bash
OLLAMA_MAX_LOADED_MODELS=1 ollama serve
```

Set `MODEL=qwen3:1.7b` in `.env` (the config's model-name variable is
shared across providers; there's no separate "Ollama model" field).

### 5. Run it

```bash
python run_agent.py
```

To crawl a page and index it first:

```bash
python run_agent.py --crawl https://example.com/some/docs/page
```

Either way, you'll land in an interactive prompt -- type a question, get
an answer grounded in the indexed content, repeat. Blank line to quit.

### Optional: Redis/MongoDB backends

These need a real server; nothing here bundles one. For local testing,
plain Docker containers are enough:

```bash
docker run -p 6379:6379 -d redis:7
docker run -p 27017:27017 -d mongo:7
```

Then set `STORE_TYPE=redis` (or `mongodb`) and the matching `STORE_HOST`/
`STORE_PORT` in `.env`.

## Configuration reference

All read through `Config` (`agent/chat/config.py`) from environment
variables / `.env`:

| Variable | Default | Notes |
|---|---|---|
| `MODEL_TYPE` | `openai` | `openai` or `open_source` |
| `MODEL` (or `OPENAI_MODEL`) | `gpt-3.5-turbo` | model name for whichever provider `MODEL_TYPE` selects |
| `OPENAI_API_KEY` | -- | required if `MODEL_TYPE=openai` |
| `STORE_TYPE` | `redis` | `chromadb`, `disk`, `redis`, or `mongodb` |
| `STORE_HOST` | `localhost` | for redis/mongodb |
| `STORE_PORT` | `6379` | for redis/mongodb |
| `NAMESPACE` | `default` | also doubles as the index key name |
| `INPUT_DIR` | `./data` | where crawled/source documents live |
| `CHUNK_SIZE` | `1024` | chunk size for splitting documents |

## Known limitations (worth knowing before you rely on this)

- **Raw LLM decode speed is a hardware ceiling, not a software problem.**
  On the machine this was built and tested on (8GB RAM, no dedicated GPU),
  a single query can take anywhere from ~20s to 90+ seconds depending on
  how many reasoning turns the agent needs. Nothing in this codebase makes
  the model itself think faster.
- **Two local models rarely fit in memory together.** An LLM and an
  embedding model loaded at once can exceed 8GB combined -- Ollama will
  swap between them, adding real latency to each query's embed step. This
  is a hardware constraint (see `OLLAMA_MAX_LOADED_MODELS` above), not a
  bug.
- **`MODEL_TYPE=open_source` needs `llama-index-embeddings-huggingface`,
  which is not in `requirements.txt`.** It was deliberately left out during
  development to prove that `MODEL_TYPE=openai` never accidentally depends
  on Ollama/HuggingFace packages. If you want to run `open_source` mode
  exactly as coded, `pip install llama-index-embeddings-huggingface`
  yourself first.
- **`MODEL_TYPE=openai` is structurally implemented and isolated, but was
  never exercised against a real OpenAI API key** during development --
  all real query testing used local Ollama models.
- **Redis and MongoDB backends need a live server** (see Setup) -- they
  are not bundled, and if untested for a while, re-verify the round trip
  before trusting them (see the comment in `requirements.txt`).
