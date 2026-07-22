from agent.chat.index import IndexManager
from agent.chat.llm import LLMManager
from agent.chat.parsing import DocumentHandler
from agent.chat.storage import StoreManager


_TOOL_DESCRIPTION = (
    "Use this tool to answer any question about the ingested documents. "
    "Always check this tool before answering from general knowledge -- it "
    "searches the actual indexed content and returns the relevant passages."
)

_FORCE_TOOL_SYSTEM_PROMPT = (
    "You have access to a knowledge_base tool that searches the ingested "
    "documents. For every user question, call knowledge_base first and "
    "answer using its returned content before considering general knowledge."
)

# Retrieve a wider candidate pool via plain vector similarity, then rerank
# down to a smaller final set with a cross-encoder before the LLM ever sees
# it -- a cross-encoder scores (query, chunk) pairs jointly, so it can catch
# genuinely-relevant chunks that plain embedding similarity ranks poorly
# (embeddings score each chunk against the query independently, with no
# interaction between the two). CANDIDATE_POOL_SIZE=10 gives the reranker
# real material to work with without pulling in so many chunks that mostly-
# irrelevant ones dilute it; RERANK_TOP_K=3 keeps the LLM's context to the
# chunks that actually matter (matches what a plain top-3 similarity search
# would have handed over anyway -- the only thing that changes is which 3).
CANDIDATE_POOL_SIZE = 10
RERANK_TOP_K = 3
# Single fixed component for now (not a registry/factory) -- there's exactly
# one reranker in play, per the task's own guidance not to over-engineer a
# swappable-provider abstraction for one option. cross-encoder/ms-marco-*
# models are trained specifically for query-passage relevance ranking
# (MS MARCO), unlike SentenceTransformerRerank's own default
# (cross-encoder/stsb-distilroberta-base, trained for STS/paraphrase
# similarity, not retrieval relevance) -- verified via inspect.signature
# against the installed llama-index-core 0.14.23, not assumed. Runs fully
# locally via sentence-transformers/torch, no cloud API call, consistent
# with this project's local-Ollama-only stance.
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _build_reranker():
    from llama_index.core.postprocessor import SentenceTransformerRerank

    return SentenceTransformerRerank(model=RERANK_MODEL, top_n=RERANK_TOP_K)


class AgentManager:
    def __init__(self, index, model_type):
        from llama_index.core.tools import QueryEngineTool

        query_engine = index.as_query_engine(
            similarity_top_k=CANDIDATE_POOL_SIZE,
            node_postprocessors=[_build_reranker()],
        )
        tool = QueryEngineTool.from_defaults(
            query_engine=query_engine,
            name="knowledge_base",
            description=_TOOL_DESCRIPTION,
        )

        if model_type == "openai":
            from llama_index.core.agent import FunctionAgent

            # initial_tool_choice is the documented mechanism for forcing a
            # named tool on the agent's first turn (verified:
            # llama_index.core.agent.workflow.function_agent.FunctionAgent.
            # initial_tool_choice, "the tool to try and force to call on the
            # first iteration of the agent"). Set for completeness/API
            # correctness, but it's a KNOWN NO-OP here: this project only
            # ever runs on Ollama/local models (never real OpenAI/Claude/
            # Gemini), and llama_index.llms.ollama's own source confirms
            # tool_choice/tool_required are dropped before reaching Ollama's
            # API ("not yet supported" upstream). So this line changes
            # nothing in practice -- the measured improvement comes entirely
            # from _TOOL_DESCRIPTION. Left in rather than removed since it's
            # harmless and correct per the documented API; don't mistake it
            # for a working forcing mechanism on this stack.
            self.agent = FunctionAgent(tools=[tool], initial_tool_choice="knowledge_base")
        else:
            from llama_index.core.agent import ReActAgent

            # ReActAgent has no initial_tool_choice equivalent (verified
            # against the installed llama-index-core: no such field on this
            # class, unlike FunctionAgent) -- text-based ReAct reasoning has
            # no native forced-tool-call mechanism, so the system_prompt is
            # the available lever here instead.
            self.agent = ReActAgent(tools=[tool], system_prompt=_FORCE_TOOL_SYSTEM_PROMPT)

    async def aquery(self, prompt):
        handler = self.agent.run(user_msg=prompt)
        return str(await handler)

    def query(self, prompt):
        # Standalone/one-off use only. Ollama caches an async client bound to
        # whatever event loop is running when it's first used (verified via
        # inspect.signature: Ollama.__init__ takes and stores an
        # async_client). Calling asyncio.run() fresh per query -- as this
        # used to do unconditionally -- creates a NEW loop each time, and the
        # second call then crashes with "RuntimeError: Event loop is closed"
        # trying to reuse the first loop's client. A multi-query session
        # (run_agent.py's interactive loop) must call aquery() directly from
        # within one long-lived asyncio.run(), not go through this method.
        import asyncio

        return asyncio.run(self.aquery(prompt))


class RAGAgent:
    def __init__(self, config):
        self.config = config
        self.storage_manager = StoreManager(config)
        self.document_handler = DocumentHandler(config)
        self.index_manager = IndexManager(self.storage_manager, self.document_handler, config)
        self.llm_manager = LLMManager(config)
        self._agent_manager = None
        self._loaded_key_name = None

    def _get_agent_manager(self, key_name):
        # Reused across every query in a session for the SAME key_name --
        # rebuilding this per query was rebuilding the reranker (a ~3s
        # cross-encoder model load, confirmed in the reranker task) and the
        # ReActAgent/FunctionAgent instance on every single call for no
        # reason. Only rebuilt if key_name changes (switching to a different
        # index mid-session, which the current single-session CLI flow
        # never actually does, but is a real possibility worth not breaking).
        if self._agent_manager is None or self._loaded_key_name != key_name:
            index = self.index_manager.load_index(key_name)
            self._agent_manager = AgentManager(index, self.config.MODEL_TYPE)
            self._loaded_key_name = key_name
        return self._agent_manager

    async def arun(self, prompt, key_name):
        return await self._get_agent_manager(key_name).aquery(prompt)

    def run(self, prompt, key_name):
        return self._get_agent_manager(key_name).query(prompt)
