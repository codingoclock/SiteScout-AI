# 🚀🤖 WebchatAI

**Open-source RAG (Retrieval-Augmented Generation) agent for websites.**

WebchatAI is a modular, flexible Python framework designed to build intelligent chat agents using LlamaIndex. It features a plugin-style architecture allowing you to easily switch between different LLMs, storage backends, and indexing strategies.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## ✨ Key Features

* **Modular Architecture**: Built using Factory patterns for easy extensibility.
* **Multiple LLM Support**:
    * **OpenAI**: GPT-3.5/4 integration.
    * **Open Source**: Integration with Ollama for local LLMs.
* **Flexible Storage Backends**:
    * **ChromaDB**: For vector storage.
    * **Redis**: For document storage and caching.
    * **MongoDB**: For scalable document and index storage.
* **Indexing Strategies**: Supports Vector Store Indexing and Summary Indexing.
* **Agentic Workflow**: Built on top of `llama-index` agents for reasoning capabilities.

## 📂 Project Structure

```text
webchatai/
├── agent/
│   └── chat/
│       ├── index.py       # Index creation and loading logic
│       ├── llm.py         # LLM (OpenAI/Ollama) wrapper
│       ├── logger.py      # Logging configuration
│       ├── manager.py     # Main RAG Agent entry point
│       ├── parsing.py     # Document parsing and node splitting
│       └── storage.py     # Storage backends (Redis/Mongo/Chroma)
├── requirements.txt
└── setup.py
