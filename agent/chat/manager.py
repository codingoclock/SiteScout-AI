from typing import List, Optional
import asyncio

# Use relative imports to avoid depending on the package being installed
from .config import Config
from .storage import StoreManager
from .index import IndexManager
from .llm import LLMManager
from .logger import Logger

# Note: llama_index imports are intentionally deferred to runtime to avoid
# import-time failures on incompatible environments.

class DocumentHandler:
    def __init__(self, input_files: List[str]):
        # Delay importing heavy dependencies until actually needed
        from llama_index.core import SimpleDirectoryReader
        from llama_index.core.node_parser import SentenceSplitter

        self.reader = SimpleDirectoryReader(input_files=input_files)
        self.parser = SentenceSplitter()

    def get_nodes(self):
        documents = self.reader.load_data()
        nodes = self.parser.get_nodes_from_documents(documents)
        return nodes

    def get_documents(self):
        documents = self.reader.load_data()
        return documents


class AgentManager:
    def __init__(self, index, model_type: str, api_key: Optional[str] = None):
        # Defer imports to runtime for clearer errors
        from llama_index.core.tools import QueryEngineTool
        from llama_index.core.tools.types import ToolMetadata

        query_tool = QueryEngineTool(
            query_engine=index.as_query_engine(),
            metadata=ToolMetadata(
                name="agent",
                description=(
                    "Answers questions related to the data. Use a detailed plain text question as input to the tool."
                ),
            ),
        )
        self.query_engine = index.as_query_engine()

        if model_type and model_type.lower() == "openai":
            from llama_index.agent.openai import OpenAIAgent

            self.agent = OpenAIAgent.from_tools(
                [query_tool], api_key=api_key, verbose=False
            )
        else:
            # Use the generic ReActAgent which will use Settings.llm set by LLMManager
            from llama_index.core.agent import ReActAgent

            self.agent = ReActAgent.from_tools([query_tool], verbose=False)

    async def chat(self, prompt: str) -> str:
        result = self.agent.chat(prompt)
        if asyncio.iscoroutine(result):
            return await result
        return result


class RAGAgent:
    def __init__(self, config: Config):
        Logger.setup()
        self.config = config

        self.storage_manager = None
        self.storage_manager = StoreManager.create(
            store_type=self.config.store_type,
            host=config.STORE_HOST,
            port=config.STORE_PORT,
            namespace=config.NAMESPACE,
            uri=config.URI,
        )

        self.document_handler = DocumentHandler(self.config.INPUT_FILES)
        self.index_manager = IndexManager.create(
            store_type=self.config.store_type,
            storage_manager=self.storage_manager,
            document_handler=self.document_handler,
            config=self.config,
        )

        self.llm_manager = LLMManager.create(
            model_type=config.MODEL_TYPE,
            api_key=config.OPENAI_API_KEY,
            model=config.MODEL,
            temperature=config.TEMPERATURE,
            chunk_size=config.CHUNK_SIZE,
            embedding_model=config.EMBEDDING_MODEL,
            cache_folder="./store/",
        )

        self.agent_manager = None

    def setup_agent(self, index):
        # Pass the configured model type and API key (if any)
        self.agent_manager = AgentManager(index, self.config.MODEL_TYPE, api_key=self.config.OPENAI_API_KEY)

    def create_index(self, key_name: str):
        self.index_manager.create_index(key_name)

    async def run(self, prompt: str, key_name: str) -> str:
        if self.index_manager.index:
            index = self.index_manager.index
        else:
            index = self.index_manager.load_index(key_name)

        self.setup_agent(index)
        return await self.agent_manager.chat(prompt)
