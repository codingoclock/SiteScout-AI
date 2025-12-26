from typing import List


class DocumentHandler:
    def __init__(self, input_files: List[str]):
        from llama_index.core import SimpleDirectoryReader
        from llama_index.core.node_parser import SentenceSplitter

        self.reader = SimpleDirectoryReader(input_files=input_files)
        self.parser = SentenceSplitter()

    def get_nodes(self):
        documents = self.reader.load_data()
        return self.parser.get_nodes_from_documents(documents)

    def get_documents(self):
        return self.reader.load_data()
