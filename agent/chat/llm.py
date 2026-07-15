class OpenAIModel:
    def __init__(self, config):
        from llama_index.core import Settings
        from llama_index.embeddings.openai import OpenAIEmbedding
        from llama_index.llms.openai import OpenAI

        Settings.llm = OpenAI(model=config.MODEL)
        Settings.embed_model = OpenAIEmbedding()


class OpenSourceModel:
    def __init__(self, config):
        from llama_index.core import Settings
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        from llama_index.llms.ollama import Ollama

        Settings.llm = Ollama(model=config.MODEL)
        Settings.embed_model = HuggingFaceEmbedding()


class ModelFactory:
    _registry = {
        "openai": OpenAIModel,
        "open_source": OpenSourceModel,
    }

    @classmethod
    def create(cls, config):
        model_cls = cls._registry.get(config.MODEL_TYPE)
        if model_cls is None:
            raise ValueError(f"Unknown MODEL_TYPE: {config.MODEL_TYPE!r}")
        return model_cls(config)


class LLMManager:
    def __init__(self, config):
        self.config = config
        self.model = ModelFactory.create(config)
