import json
import os


def _index_id_path(key_name, filename):
    return os.path.join(".", "storage", key_name, filename)


def _store_index_id(path, index_id):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"index_id": index_id}, f)


def _load_index_id(path):
    with open(path) as f:
        return json.load(f)["index_id"]


class ChromaIndex:
    def __init__(self, storage_manager, document_handler, config):
        self.storage_manager = storage_manager
        self.document_handler = document_handler
        self.config = config
        self.storage_context = storage_manager.get_storage_context()

    def create_index(self, key_name):
        from llama_index.core import VectorStoreIndex

        nodes = self.document_handler.get_nodes()
        return VectorStoreIndex(nodes, storage_context=self.storage_context)

    def load_index(self, key_name):
        from llama_index.core import VectorStoreIndex

        return VectorStoreIndex.from_vector_store(self.storage_context.vector_store)


class DiskIndex:
    def __init__(self, storage_manager, document_handler, config):
        self.storage_manager = storage_manager
        self.document_handler = document_handler
        self.config = config
        self.storage_context = storage_manager.get_storage_context()

    def create_index(self, key_name):
        from llama_index.core import VectorStoreIndex

        nodes = self.document_handler.get_nodes()
        index = VectorStoreIndex(nodes, storage_context=self.storage_context)
        self.storage_context.persist(persist_dir=f"./storage/{key_name}")
        return index

    def load_index(self, key_name):
        from llama_index.core import StorageContext, load_index_from_storage

        storage_context = StorageContext.from_defaults(persist_dir=f"./storage/{key_name}")
        return load_index_from_storage(storage_context)


class RedisIndex:
    def __init__(self, storage_manager, document_handler, config):
        self.storage_manager = storage_manager
        self.document_handler = document_handler
        self.config = config
        self.storage_context = storage_manager.get_storage_context()

    def create_index(self, key_name):
        from llama_index.core import SummaryIndex

        nodes = self.document_handler.get_nodes()
        index = SummaryIndex(nodes, storage_context=self.storage_context)
        _store_index_id(_index_id_path(key_name, "redis_index_id.json"), index.index_id)
        return index

    def load_index(self, key_name):
        from llama_index.core import load_index_from_storage

        index_id = _load_index_id(_index_id_path(key_name, "redis_index_id.json"))
        return load_index_from_storage(self.storage_context, index_id=index_id)
    


class MongoIndex:
    def __init__(self, storage_manager, document_handler, config):
        self.storage_manager = storage_manager
        self.document_handler = document_handler
        self.config = config
        self.storage_context = storage_manager.get_storage_context()

    def create_index(self, key_name):
        from llama_index.core import SummaryIndex

        nodes = self.document_handler.get_nodes()
        index = SummaryIndex(nodes, storage_context=self.storage_context)
        _store_index_id(_index_id_path(key_name, "mongo_index_id.json"), index.index_id)
        return index

    def load_index(self, key_name):
        from llama_index.core import load_index_from_storage

        index_id = _load_index_id(_index_id_path(key_name, "mongo_index_id.json"))
        return load_index_from_storage(self.storage_context, index_id=index_id)


class IndexFactory:
    _registry = {
        "chromadb": ChromaIndex,
        "disk": DiskIndex,
        "redis": RedisIndex,
        "mongodb": MongoIndex,
    }

    @classmethod
    def create(cls, storage_manager, document_handler, config):
        index_cls = cls._registry.get(config.STORE_TYPE)
        if index_cls is None:
            raise ValueError(f"Unknown STORE_TYPE: {config.STORE_TYPE!r}")
        return index_cls(storage_manager, document_handler, config)


class IndexManager:
    def __init__(self, storage_manager, document_handler, config):
        self.config = config
        self.index_backend = IndexFactory.create(storage_manager, document_handler, config)

    def create_index(self, key_name):
        return self.index_backend.create_index(key_name)

    def load_index(self, key_name):
        return self.index_backend.load_index(key_name)
