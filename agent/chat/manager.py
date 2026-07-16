from agent.chat.index import IndexManager
from agent.chat.llm import LLMManager
from agent.chat.parsing import DocumentHandler
from agent.chat.storage import StoreManager


class AgentManager:
    def __init__(self, index, model_type):
        from llama_index.core.tools import QueryEngineTool

        query_engine = index.as_query_engine()
        tool = QueryEngineTool.from_defaults(
            query_engine=query_engine,
            name="knowledge_base",
            description="Query the indexed documents.",
        )

        if model_type == "openai":
            from llama_index.core.agent import FunctionAgent

            self.agent = FunctionAgent(tools=[tool])
        else:
            from llama_index.core.agent import ReActAgent

            self.agent = ReActAgent(tools=[tool])

    def query(self, prompt):
        import asyncio

        async def _run():
            handler = self.agent.run(user_msg=prompt)
            return await handler

        return str(asyncio.run(_run()))


class RAGAgent:
    def __init__(self, config):
        self.config = config
        self.storage_manager = StoreManager(config)
        self.document_handler = DocumentHandler(config)
        self.index_manager = IndexManager(self.storage_manager, self.document_handler, config)
        self.llm_manager = LLMManager(config)

    def run(self, prompt, key_name):
        index = self.index_manager.load_index(key_name)
        agent_manager = AgentManager(index, self.config.MODEL_TYPE)
        return agent_manager.query(prompt)
