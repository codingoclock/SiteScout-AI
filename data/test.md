# SiteScout AI Test Document

This is the first paragraph of a throwaway test document used to verify
that DocumentHandler correctly loads files from a directory using
SimpleDirectoryReader with the input_dir parameter, rather than input_files.

This is a second paragraph with different content, so that SentenceSplitter
has more than one sentence to work with when it splits this document into
nodes based on the configured chunk size.

Here is a third paragraph. It has multiple short sentences. Each one should
still be captured. The splitter should produce at least one node, and likely
more than one if the chunk size is small enough relative to this text.
