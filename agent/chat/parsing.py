from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter


class DocumentHandler:
    def __init__(self, config):
        self.config = config

    def get_documents(self):
        reader = SimpleDirectoryReader(input_dir=self.config.INPUT_DIR)
        return reader.load_data()

    def get_nodes(self):
        documents = self.get_documents()
        splitter = SentenceSplitter(chunk_size=self.config.CHUNK_SIZE)
        return splitter.get_nodes_from_documents(documents)
