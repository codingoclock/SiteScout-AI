class ChromaStorage:
    def __init__(self, host, port, namespace, uri=None):
        import chromadb
        from llama_index.vector_stores.chroma import ChromaVectorStore

        client = chromadb.EphemeralClient()
        collection = client.get_or_create_collection(namespace)
        self.vector_store = ChromaVectorStore(chroma_collection=collection)

    def get_storage_context(self):
        from llama_index.core import StorageContext

        return StorageContext.from_defaults(vector_store=self.vector_store)


class DiskStorage:
    def __init__(self, host, port, namespace, uri=None):
        self.persist_dir = f"./storage/{namespace}"

    def get_storage_context(self):
        import os

        from llama_index.core import StorageContext

        if os.path.exists(self.persist_dir):
            return StorageContext.from_defaults(persist_dir=self.persist_dir)
        return StorageContext.from_defaults()


class RedisStorage:
    def __init__(self, host, port, namespace, uri=None):
        from llama_index.storage.docstore.redis import RedisDocumentStore
        from llama_index.storage.index_store.redis import RedisIndexStore

        self.docstore = RedisDocumentStore.from_host_and_port(host, port, namespace=namespace)
        self.index_store = RedisIndexStore.from_host_and_port(host, port, namespace=namespace)

    def get_storage_context(self):
        from llama_index.core import StorageContext

        return StorageContext.from_defaults(docstore=self.docstore, index_store=self.index_store)


class MongoStorage:
    def __init__(self, host, port, namespace, uri=None):
        from llama_index.storage.docstore.mongodb import MongoDocumentStore
        from llama_index.storage.index_store.mongodb import MongoIndexStore

        if uri:
            self.docstore = MongoDocumentStore.from_uri(uri, namespace=namespace)
            self.index_store = MongoIndexStore.from_uri(uri, namespace=namespace)
        else:
            self.docstore = MongoDocumentStore.from_host_and_port(host, port, namespace=namespace)
            self.index_store = MongoIndexStore.from_host_and_port(host, port, namespace=namespace)

    def get_storage_context(self):
        from llama_index.core import StorageContext

        return StorageContext.from_defaults(docstore=self.docstore, index_store=self.index_store)


class StorageFactory:
    _registry = {
        "chromadb": ChromaStorage,
        "disk": DiskStorage,
        "redis": RedisStorage,
        "mongodb": MongoStorage,
    }

    @classmethod
    def create(cls, config, uri=None):
        storage_cls = cls._registry.get(config.STORE_TYPE)
        if storage_cls is None:
            raise ValueError(f"Unknown STORE_TYPE: {config.STORE_TYPE!r}")
        return storage_cls(
            host=config.STORE_HOST,
            port=config.STORE_PORT,
            namespace=config.NAMESPACE,
            uri=uri,
        )


class StoreManager:
    def __init__(self, config, uri=None):
        self.config = config
        self.storage = StorageFactory.create(config, uri=uri)

    def get_storage_context(self):
        return self.storage.get_storage_context()
