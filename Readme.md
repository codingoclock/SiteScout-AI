# 🔍 SiteScout AI — Website Intelligence with RAG

**An open-source, agentic Retrieval-Augmented Generation (RAG) framework for websites, powered by LlamaIndex.**

> Website Ingestion • Vector Search • Agentic Reasoning • Plug-and-Play LLMs

[![Python](https://img.shields.io/badge/Python-3.10%20|%203.11%20|%203.12-blue)](https://www.python.org/)
[![LlamaIndex](https://img.shields.io/badge/LlamaIndex-RAG-purple)](https://github.com/run-llama/llama_index)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT-black)](https://platform.openai.com/)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLMs-orange)](https://ollama.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-VectorDB-green)](https://www.trychroma.com/)
[![Redis](https://img.shields.io/badge/Redis-Cache-red)](https://redis.io/)
[![MongoDB](https://img.shields.io/badge/MongoDB-NoSQL-brightgreen)](https://www.mongodb.com/)
[![Status](https://img.shields.io/badge/Status-Active--Development-brightblue)](#-quick-start)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)


---

## 🚨 Python Version Requirement (Strict)

**SiteScout AI runs ONLY on Python 3.10, 3.11, or 3.12**

❌ Python ≤ 3.9 → **Not supported**  
❌ Python ≥ 3.13 → **Not tested**

This constraint exists due to:
- LlamaIndex internal dependencies
- Async event-loop compatibility
- Vector store bindings

👉 **If your Python version is outside this range, the project will not run.**

---

## 🚀 What Is SiteScout AI?

SiteScout AI converts websites into **intelligent, queryable knowledge bases** using Retrieval-Augmented Generation (RAG).

Instead of relying on static prompts, SiteScout:
- Parses website content into structured documents
- Generates vector embeddings
- Stores them in pluggable vector stores
- Uses **agent-based reasoning** to answer questions accurately

Think:
> *“ChatGPT, but grounded strictly in my website’s content.”*

---

## ✨ Key Features

### 🧩 Modular Architecture
- Factory-pattern design
- Swap LLMs, storage backends, and indexes without refactoring
- Clean separation of concerns

### 🧠 Multiple LLM Providers
- **OpenAI** (GPT-3.5 / GPT-4)
- **Ollama** (local open-source models)
- Easy extension for future providers

### 🗄️ Flexible Storage Backends
- **ChromaDB** — vector embeddings
- **Redis** — document caching
- **MongoDB** — scalable document & index storage

### 📚 Indexing Strategies
- Vector Store Index
- Summary Index
- Hybrid-ready design

### 🤖 Agentic RAG Workflow
- Built on `llama-index` agents
- Multi-step reasoning
- Context-aware, grounded responses

---

## ⚡ Quick Start

### ✅ Prerequisites
- **Python 3.10 / 3.11 / 3.12**
- pip
- (Optional) Ollama for local LLMs

Verify Python version:
```bash
python --version
```
## 🧬 Installation
### 1️⃣ Clone the Repository
```bash
git clone https://github.com/codingoclock/ProsZ-Future-Prosthetics.git
cd ProsZ-Future-Prosthetics
```
### 2️⃣ Install Dependencies
```bash 
pip install -r requirements.txt
```
## ⚙️ Configuration
#### SiteScout AI uses environment variables for LLMs and storage backends.
### 🔑 OpenAI
```bash
export OPENAI_API_KEY=your_openai_api_key
```
## 🧠 Ollama (Local LLMs)
``` bash
ollama serve
```
#### Ensure a model is available:
``` bashh
ollama pull mistral
```
## 🗄️ Redis
```bash
export STORE_HOST=localhost
export STORE_PORT=6379
```
## 🍃 MongoDB
``` bash
export URI=mongodb+srv://your_cluster_url
```
## ▶️ Running the RAG Agent
``` bash
from sitescoutai.agent.chat.manager import RAGManager
from sitescoutai.config import Config

config = Config()
agent = RAGManager(config)

response = agent.query("Hello, SiteScout!")
print(response)
```
## 📁 Project Structure
```
SiteScoutAI/
├── .venv/
│
├── agent/
│   ├── __init__.py
│   │
│   ├── chat/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── index.py
│   │   ├── llm.py
│   │   ├── manager.py
│   │   ├── parsing.py
│   │   ├── storage.py
│   │   └── logger.py
│   │
│   ├── crawler/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── sitemap.py
│   │   └── url_manager.py
│
├── .env
├── .env.example
├── run_agent.py
├── requirements.txt
├── setup.py
├── README.md
├── .gitignore
└── pyvenv.cfg
```
## 🔄 RAG Workflow
```bash
Website Content
      ↓
Document Parsing & Chunking
      ↓
Vector Embeddings
      ↓
Vector Store (ChromaDB)
      ↓
Agent Reasoning (LlamaIndex)
      ↓
Final Answer
```
## 🎯 Use Cases
- Website chatbots
- Documentation assistants
- Product knowledge bases
- Customer support automation
- Developer portals
- Research & internal tools

## 🐛 Troubleshooting
### ❌ Project fails to start
```bash
python --version
# Must be 3.10–3.12
```
### Reinstall dependencies:
``` bash
pip install -r requirements.txt --force-reinstall
```

### ❌ Ollama not responding
``` bash
ollama serve
```
### Check model availability:
```bash
ollama list
```
### ❌ Vector store issues
- Ensure ChromaDB directory permissions
- Restart Redis / MongoDB if enabled
- Clear cached indexes after schema changes

## 📈 Roadmap
- Website crawler integration
- Streaming responses
- Hybrid search (BM25 + vector)
- Multi-agent collaboration
- FastAPI API layer
- Authentication & access control
- Dashboard UI
- Docker & Kubernetes support
  
## 📄 License
- MIT License

## 👥 Contributing
### Contributions are welcome!
- Fork the repository
- Create a feature branch
- Submit a pull request
- Open issues for bugs or enhancements

### If this project helped you, consider giving it a ⭐ on GitHub.
 
