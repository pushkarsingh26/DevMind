<div align="center">
  <a href="https://github.com/pushkarsingh26/DevMind">
    <svg width="800" height="220" viewBox="0 0 800 220" fill="none" xmlns="http://www.w3.org/2000/svg" style="max-width: 100%; height: auto; background: #0b111e; border-radius: 12px; border: 1px solid #1f2937; box-shadow: 0 10px 30px rgba(0,0,0,0.6);">
      <!-- Background Grid -->
      <path d="M 0,40 H 800 M 0,80 H 800 M 0,120 H 800 M 0,160 H 800 M 0,200 H 800" stroke="#111827" stroke-width="1"/>
      <path d="M 100,0 V 220 M 200,0 V 220 M 300,0 V 220 M 400,0 V 220 M 500,0 V 220 M 600,0 V 220 M 700,0 V 220" stroke="#111827" stroke-width="1"/>
      
      <!-- Nodes / Connections (Neural Net Representation) -->
      <g stroke="#1f2937" stroke-width="1.5">
        <line x1="80" y1="50" x2="160" y2="70" />
        <line x1="80" y1="50" x2="120" y2="130" />
        <line x1="160" y1="70" x2="220" y2="50" />
        <line x1="120" y1="130" x2="220" y2="160" />
        <line x1="220" y1="50" x2="300" y2="110" />
        <line x1="220" y1="160" x2="300" y2="110" />
        <line x1="300" y1="110" x2="420" y2="110" stroke="#0ea5e9" stroke-width="2.5"/>
        <line x1="420" y1="110" x2="500" y2="60" />
        <line x1="420" y1="110" x2="480" y2="150" />
        <line x1="500" y1="60" x2="620" y2="80" />
        <line x1="480" y1="150" x2="580" y2="170" />
        <line x1="620" y1="80" x2="720" y2="130" />
        <line x1="580" y1="170" x2="720" y2="130" />
      </g>
      
      <!-- Glowing Connector Nodes -->
      <circle cx="80" cy="50" r="4" fill="#6b7280" />
      <circle cx="160" cy="70" r="5" fill="#0ea5e9" opacity="0.8"/>
      <circle cx="120" cy="130" r="4" fill="#3b82f6" />
      <circle cx="220" cy="50" r="6" fill="#a855f7" />
      <circle cx="220" cy="160" r="5" fill="#312e81" />
      <circle cx="300" cy="110" r="8" fill="#0ea5e9" style="filter: drop-shadow(0px 0px 8px #0ea5e9);"/>
      <circle cx="420" cy="110" r="8" fill="#22d3ee" style="filter: drop-shadow(0px 0px 8px #22d3ee);"/>
      <circle cx="500" cy="60" r="4" fill="#6b7280" />
      <circle cx="480" cy="150" r="5" fill="#ec4899" />
      <circle cx="620" cy="80" r="6" fill="#10b981" />
      <circle cx="580" cy="170" r="4" fill="#f59e0b" />
      <circle cx="720" cy="130" r="5" fill="#22d3ee" />
      
      <!-- Logo Typography -->
      <text x="400" y="85" font-family="system-ui, -apple-system, sans-serif" font-size="40" font-weight="900" fill="#ffffff" text-anchor="middle" letter-spacing="4px">DEVMIND</text>
      <text x="400" y="120" font-family="monospace" font-size="12" font-weight="600" fill="#0ea5e9" text-anchor="middle" letter-spacing="6px">AI CODE INTELLIGENCE ENGINE</text>
      <text x="400" y="150" font-family="system-ui, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#8892b0" text-anchor="middle" letter-spacing="1px">RAG GROUNDED SEMANTIC PIPELINE • MULTI-AGENT ARCHITECTURE</text>
      <text x="400" y="175" font-family="system-ui, -apple-system, sans-serif" font-size="9" font-weight="500" fill="#6b7280" text-anchor="middle" letter-spacing="2px">PHASE 5 ENGINE COMPLETE</text>
    </svg>
  </a>

  <h1>🧠 DevMind — AI Code Intelligence Engine</h1>
  <p><b>Context-Grounded Multi-Agent Code Audits & Semantic RAG Repository Chat</b></p>

  <p>
    <a href="https://github.com/pushkarsingh26/DevMind/releases"><img src="https://img.shields.io/badge/version-0.5.0-cyan.svg?style=flat-square" alt="Current Version"></a>
    <img src="https://img.shields.io/badge/Phase-5--Complete-emerald.svg?style=flat-square" alt="Phase 5 Completed">
    <img src="https://img.shields.io/badge/Python-3.10-blue.svg?style=flat-square" alt="Python Version">
    <img src="https://img.shields.io/badge/FastAPI-0.100+-green.svg?style=flat-square" alt="FastAPI">
    <img src="https://img.shields.io/badge/React-TypeScript-blue.svg?style=flat-square" alt="React & TypeScript">
    <img src="https://img.shields.io/badge/Vector%20Store-FAISS-purple.svg?style=flat-square" alt="FAISS Vector Store">
    <img src="https://img.shields.io/badge/LLM-Gemini%20%2F%20Ollama-orange.svg?style=flat-square" alt="LLMs supported">
    <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-lightgrey.svg?style=flat-square" alt="MIT License"></a>
  </p>

  <h4>
    <a href="#🚀-features">Features</a> •
    <a href="#🏛️-architecture-overview">Architecture</a> •
    <a href="#⚙️-installation--setup">Setup</a> •
    <a href="#🔌-api-overview">API Specs</a> •
    <a href="#🛣️-project-roadmap">Roadmap</a>
  </h4>
</div>

---

## 📖 Introduction

**DevMind** is a flagship context-grounded AI Code Intelligence Engine designed to automate repository scans, structural analysis, and interactive code exploration. By extracting structured syntax metadata and compiling entire codebases into semantic vector stores, DevMind eliminates the "context drift" and "hallucination" problems commonly associated with code explanation engines. 

Developers can upload repository ZIP archives or paste public GitHub repository links. DevMind immediately indexes the workspace, creates optimized vector embedding chunks, runs specialized agents (Planner, Reviewer, Security, Critic) through a resilient model-failover pipeline, and serves a live Grounded Chat workspace.

### The Problem It Solves
Traditional LLMs fail on codebases because:
1. **Context Limits:** Inserting an entire codebase into a single context window is expensive and results in degraded reasoning quality (lost-in-the-middle).
2. **Context Drift:** Standard retrieval systems return too much noise, retrieving file lockfiles, package lists, or testing fixtures rather than core business logic.
3. **Truncated JSON Responses:** LLM APIs often stream incomplete or malformed JSON payloads, breaking frontend parsers and crashing chat sessions.

### Why it is Valuable for Developers
DevMind fixes these problems by building a highly localized **Retrieval-Augmented Generation (RAG)** pipeline. It filters lockfiles out of the vector pipeline, scores search queries with path-based reranking, repairs truncated JSON payloads using backtracking string-matching, and extracts code citations directly linked to specific lines in your repository. It acts as an autonomous code auditor and conversational partner that *actually* knows your codebase.

---

## 🚀 Features

* 📁 **Smart Repository Ingestion:** Direct support for remote Git repository cloning (depth 1) and local ZIP upload handling.
* 🔍 **Static Structural Analyzer:** Identifies languages, frameworks, package structures, dependency listings, and file stats automatically.
* 🤖 **Multi-Provider Failover Chain:** Resilient AI reasoning querying multiple cloud providers with graceful fallbacks to local heuristic models if LLMs are offline.
* 🧠 **Semantic Search & RAG:** Generates vector embeddings via Google AI / HuggingFace models, indexing them into local FAISS vector stores with code-path score boosting.
* 💬 **Streaming Grounded Chat:** Multi-turn conversational interface displaying real-time markdown answers, interactive code previews, line citations, and clickable follow-up suggestions.
* 📤 **Multi-format Exports:** Instantly export chat transcripts as Markdown (.md) documents or render print-friendly PDF booklets directly from the UI.
* 🛡️ **Noisy Dependency Filtering:** Automatically bypasses `package-lock.json`, `yarn.lock`, `node_modules`, and minified assets during chunking to focus strictly on business logic.

---

## 🏛️ Architecture Overview

The system consists of a microservice-style FastAPI backend orchestrating repository downloads and vector stores, alongside a responsive, dark-themed React SPA frontend.

```mermaid
graph TD
    %% Client & Routing
    User([Developer / Recruiter]) -->|Upload ZIP / GitHub URL| ReactApp[React + TS SPA]
    ReactApp -->|HTTP requests / SSE Stream| FastAPI[FastAPI Backend Router]

    %% Ingestion & Scanner
    FastAPI -->|Job Dispatch| PipelineService[Pipeline Service]
    PipelineService -->|Clone/Extract| RepoService[Repository Service]
    RepoService -->|Local Workspace Files| ScannerService[Static Scanner Service]
    ScannerService -->|Framework/Language Metadata| DB[(PostgreSQL Database)]

    %% Chunking & Vector DB
    PipelineService -->|Raw Code files| ChunkService[Chunk Service]
    ChunkService -->|Code Chunks| RAGService[RAG Service]
    RAGService -->|Generate Embeddings| EmbeddingService[Embedding Service]
    EmbeddingService -->|FAISS vectors| VectorStore[FAISS Vector Store Disk]

    %% Chat & LLM Grounding
    ReactApp -->|Grounded Questions| ChatRouter[Chat API Router]
    ChatRouter -->|Retrieval Query| RetrievalService[Retrieval Service]
    RetrievalService -->|FAISS Search + Path Boost Rerank| VectorStore
    RetrievalService -->|High-quality Source Chunks| PromptBuilder[Chat Prompt Builder]
    PromptBuilder -->|Context-grounded Messages| AIOrchestrator[Conversation Service]
    AIOrchestrator -->|Model Failover Pipeline| LLMChain{Cloud Providers / Ollama}
    LLMChain -->|JSON Response| ResponseParser[Response Parser + JSON Repair]
    ResponseParser -->|Clean Markdown Answer + Citations| ReactApp
```

---

## 📊 How DevMind Works

Below is the workflow sequence showing how DevMind processes a codebase, indexes it semantically, and returns context-grounded chat responses with robust JSON repair.

```mermaid
sequenceDiagram
    autonumber
    actor User as Developer
    participant UI as React UI Workspace
    participant API as FastAPI Router
    participant RAG as Retrieval & Chunking
    participant DB as Postgres & FAISS
    participant LLM as LLM Cloud Providers
    
    User->>UI: Submit Git URL / ZIP Archive
    UI->>API: POST /api/analyze/git
    API->>RAG: Clone & static scan workspace
    RAG->>RAG: Filter lockfiles (package-lock.json, etc.)
    RAG->>DB: Save repository metadata
    RAG->>DB: Generate embeddings & build FAISS Vector Store
    API->>UI: Return analysis completed (Auto-bind)
    
    User->>UI: Ask grounded question
    UI->>API: GET /chat/stream?message=...
    API->>DB: Query FAISS store for query similarity
    DB->>API: Return top vector chunks
    API->>API: Apply path-based reranking (READMEs, app/*)
    API->>LLM: Send prompt containing query + context chunks
    LLM-->>API: Stream JSON chunks (answer + citations)
    API->>API: Parse tokens via StreamingAnswerExtractor
    API-->>UI: Stream clean Markdown tokens (Server-Sent Events)
    
    Note over API,LLM: In case LLM returns truncated or broken JSON
    API->>API: Apply parenthesis closure & backtracking repair
    API-->>UI: Yield repaired markdown answer stream
```

---

## ⚙️ Technology Stack

| Layer | Component | Technologies | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend** | Core Framework | `Python 3.10`, `FastAPI` | High-performance asynchronous API routing |
| **Backend** | Database & ORM | `PostgreSQL`, `SQLAlchemy`, `Alembic` | Relational storage for repos, jobs, and chat history |
| **Backend** | Vector Index | `FAISS` (Facebook AI Similarity Search) | Local similarity search for code chunk vectors |
| **Backend** | Models & Parsers | `Pydantic v2`, `HuggingFace`, `Google Gemini` | Schema validation, semantic embeddings, and LLM text generation |
| **Frontend** | Build System | `Node.js`, `Vite`, `TypeScript` | Modern production assets bundling |
| **Frontend** | Library Core | `React 18`, `React Router v6`, `React Context` | Component logic and global application state |
| **Frontend** | Styling & Theme | `Vanilla CSS`, `TailwindCSS` | Glassmorphic dark styling and layout responsiveness |
| **Frontend** | Icons & Highlights | `Lucide React`, `highlight.js` | Interactive UI elements and code formatting |

---

## 📂 Project Structure

<details>
<summary>📂 Click to view Directory Trees</summary>

### Backend Workspace Structure
```
backend/
├── alembic/                  # Database migration version files
├── app/
│   ├── ai/                   # AI Provider clients and prompt registry
│   ├── api/                  # API routers, endpoint schemas, dependencies
│   ├── chat/                 # Grounded chat service, schemas, prompts, parser
│   ├── core/                 # Configs, logger, security handlers
│   ├── db/                   # DB engine, session builder, registry base
│   ├── models/               # SQLAlchemy ORM models (Repository, Chat, Embeddings)
│   ├── services/             # Pipeline, scanning, chunking, RAG services
│   ├── utils/                # JSON repair helpers, git helpers, file utilities
│   └── main.py               # Main ASGI Application entry point
├── tests/                    # 38 pytest unit & integration test suites
├── alembic.ini               # Alembic configuration
└── poetry.lock / pyproject   # Python package dependencies
```

### Frontend Workspace Structure
```
src/
├── assets/                   # Static global styling and SVG banners
├── chat/
│   ├── components/           # ChatWindow, ChatSidebar, ChatMessage, CitationCard, ExportMenu
│   ├── ChatContext.tsx       # State management for grounded chat
│   ├── api.ts                # SSE Fetch API and conversation services
│   ├── chat.css              # Custom layout CSS with print queries
│   └── types.ts              # TypeScript interfaces
├── components/               # Dashboard cards, output panel, intelligence components
├── context/                  # AnalysisContext state
├── hooks/                    # useAnalysis hook
├── layouts/                  # Layout shell (Navbar, MainLayout, Footer)
├── pages/                    # Dashboard and ChatPage
├── types/                    # Report, Agent, Toast types
├── App.tsx                   # Main Routing core
└── main.tsx                  # Vite render mount
```
</details>

---

## ⚙️ Installation & Setup

### Environment Variables
Create a `.env` file inside the `backend/` directory:
```bash
# Core Server Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/devmind
WORKSPACE_ROOT=./temp_workspace
SECRET_KEY=devmind_secure_key_here

# Cloud LLM Provider Credentials
GOOGLE_API_KEY=AIzaSy...
GOOGLE_MODEL_NAME=gemini-2.5-flash
GROQ_API_KEY=gsk_...
GROQ_MODEL_NAME=llama3-70b-8192

# Local LLM Support (Ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_NAME=llama3.2
```

### Backend Setup
Ensure you have Python 3.10 and PostgreSQL installed.
```bash
# Navigate to backend directory
cd backend

# Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run migrations to update database tables
alembic upgrade head

# Start the FastAPI development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend Setup
Ensure you have Node.js (v18+) installed.
```bash
# Install package dependencies
npm install

# Start the Vite local development server
npm run dev

# Compile production bundle
npm run build
```

---

## 🔌 API Overview

| Method | Endpoint | Description | Payload / Query |
| :--- | :--- | :--- | :--- |
| **POST** | `/api/analyze/upload` | Upload a ZIP repo and queue analysis | Multipart form file, `task_type` |
| **POST** | `/api/analyze/git` | Clone a Git URL and queue analysis | JSON: `{repo_url, task_type}` |
| **GET** | `/api/analyze/status/{job_id}` | Polling status of analysis job | path parameter |
| **GET** | `/repositories` | List unique indexed repositories | Query params: none |
| **POST** | `/chat/conversations` | Start a new chat conversation session | JSON: `{repository_id, title}` |
| **GET** | `/chat/conversations` | List conversations for repository | Query: `repository_id`, `search` |
| **DELETE** | `/chat/conversations/{id}` | Delete a conversation session | path parameter |
| **GET** | `/chat/conversations/{id}/messages` | Paginated messages for session | Query: `limit`, `offset` |
| **GET** | `/chat/stream` | Multi-turn Grounded Chat SSE Stream | Query: `conversation_id`, `message` |

---

## 📸 Screenshots & Previews

### Grounded Chat Preview
The multi-turn chat workspace provides a mobile sidebar toggle, expandable source code citation details, and quick suggestions.
```
+-----------------------------------------------------------------------------------+
| [Sessions Sidebar]          | Grounded: owner/repo / General Grounded Chat        |
| +-------------------------+ +---------------------------------------------------+ |
| | (+) NEW CHAT            | | User: How do the models work in this codebase?    | |
| | ----------------------- | |                                                   | |
| | General Grounded Chat   | | DevMind AI: django models are in `models.py`.     | |
| | Auth Logic Check        | | They extend `models.Model` to create tables.      | |
| |                         | |                                                   | |
| | ----------------------- | | [+] Sources Cited:                                | |
| | [Export Chat (MD/PDF)]  | | - models.py (L10-L20) [Copy Code]                 | |
| +-------------------------+ +---------------------------------------------------+ |
|                           | | [ Ask a question...                     ] [ Send ]  | 
+-----------------------------------------------------------------------------------+
```

### AI Report Preview
Comprehensive codebase structural diagnostics, file hierarchies, and structural reports built on multi-agent execution.
```
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  01. Target Repository                        02. Agent Pipeline Status           |
|  +---------------------------------------+    +--------------------------------+  |
|  | GitHub URL: [ github.com/owner/repo ] |    | STAGE: Reviewer stage          |  |
|  +---------------------------------------+    | PROGRESS: [=======>    ] 60%   |  |
|                                               +--------------------------------+  |
|                                                                                   |
|  03. Repository Intelligence                  04. Analysis Report Output          |
|  +---------------------------------------+    +--------------------------------+  |
|  | Language: Python  | Files: 231        |    | # Code Review & Architecture   |  |
|  | Framework: Django | Dirs: 34          |    | - Models are clean...          |  |
|  +---------------------------------------+    +--------------------------------+  |
+-----------------------------------------------------------------------------------+
```

### Repository Intelligence Preview
Dynamic workspace mapping indicating language composition, dependencies, tests presence, and framework information.
```
+-----------------------------------------------------------------------------------+
|  Active Repo: devmind-engine/core  | Language: TS (64%), Python (30%), Shell (6%) |
|  -------------------------------------------------------------------------------  |
|  [ Frameworks ]   FastAPI, Vite React  | [ Tests ]  pytest (Py), jest (JS)        |
|  [ Package Mgr ]  poetry, npm          | [ Readme ] README.md present (MIT)       |
|  [ Largest Fs ]   app/main.py (14KB), src/chat/ChatContext.tsx (11KB)             |
+-----------------------------------------------------------------------------------+
```

---

## 📤 Export Features

* **Markdown Export:** Converts the entire message history into readable Markdown files with blockquotes, syntax highlights, code segments, and citations, downloading directly via browser.
* **Print to PDF booklet:** Uses bespoke `@media print` CSS overrides inside [chat.css](file:///c:/Users/aishw/Desktop/Projects/DevMind/src/chat/chat.css) to strip sidebar templates, input fields, navigation blocks, and margins. Renders a polished print document that recruiters can read directly.

---

## ⚡ Performance Highlights

1. **DB Connection Releasing:** Database session handles are immediately committed and closed before invoking downstream LLM streaming endpoints. This ensures PostgreSQL pools are never locked or exhausted during long streaming operations.
2. **Fast Reranking Slicing:** Embeddings database queries are optimized to fetch a wider candidate list (`k=20`), rerank paths in memory using O(N) regex filters, and truncate results to standard sizes. This delivers sub-millisecond retrieval cycles.
3. **Noisy Assets Exclusion:** Skipping lockfiles reduces vector database size by **over 70%** in typical Node/Python workspaces, minimizing FAISS search space and significantly improving query response times.

---

## 🛡️ Security Features

1. **Local Workspace Erasure:** Cloned repositories and uploaded files are analyzed, indexed, and immediately pruned from disk once database loading and vector storage are complete.
2. **Secure Key Isolation:** API keys are never persisted in databases; they are read strictly from OS environment variables.
3. **Regex PII Scrubbing:** Logs automatically sanitize sensitive strings like repository auth tokens.

---

## 💡 Why DevMind

DevMind is built for teams who want to chat with their code securely and efficiently without relying on third-party cloud wrappers that index your files indefinitely. With custom JSON recovery, local FAISS structures, and support for failover models (including local Ollama), it offers unmatched resilience, privacy, and speed in repository exploration.

---

## 🔮 Future Vision

* **Local RAG Airgap:** Full airgapped deployment support running local sentence-transformers embeddings and local Ollama models on consumer hardware.
* **Agent Collaborative Workspace:** Support for concurrent multi-agent executions where Planner, Critic, Security, and Architect agents debate codebase designs before outputting reports.
* **GitHub Actions integration:** Automated PR review bots that trigger semantic RAG checks on commit diffs before merging.

---

## 🗺️ Project Development Roadmap

### Development Status

| Status | Phase | Description | Key Deliverables |
| :---: | :--- | :--- | :--- |
| **✅** | **Phase 1** | Project Foundation | Cloner, FastAPI API, React Frontend, PostgreSQL |
| **✅** | **Phase 2** | Repository Intelligence | Static scanner, Framework/Language stats, Local cache |
| **✅** | **Phase 3** | AI Analysis Engine | Prompt system, failover chain, parser retry mechanisms |
| **✅** | **Phase 4** | Code Intelligence Dashboard | Dynamic UI timeline, cache metrics, Markdown & PDF export |
| **✅** | **Phase 5** | Grounded AI Chat | FAISS vector indexing, RAG, Citations, Streaming filters |
| **🔄** | **Phase 6** | Multi-Agent Intelligence | Planner, Reviewer, Security agents executing in parallel |
| **🔄** | **Phase 7** | GitHub Developer Workflow | Pull request review automation, inline diff review comments |
| **🔄** | **Phase 8** | Documentation Intelligence | UML generation, dependency graphs, auto README generator |
| **🔄** | **Phase 9** | Security & DevOps Audit | Vuln analysis, Dockerfile review, CI/CD audit logs |
| **🔄** | **Phase 10**| Collaboration Platform | Multi-user workspaces, auth, organization metrics |
| **🔄** | **Phase 11**| IDE Integrations | VS Code extensions, JetBrains plugins, terminal CLI |
| **🔄** | **Phase 12**| Enterprise Platform | MCP integration, local LLM Ollama configurations |

---

## 🤝 Contributing

We welcome contributions! Please open an issue or submit a pull request for any bug fixes, UI improvements, or roadmap suggestions.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENCE](file:///c:/Users/aishw/Desktop/Projects/DevMind/LICENCE) file for details.

---

## 💖 Acknowledgements

* **FastAPI** for ASGI routing capabilities.
* **FAISS** for fast similarity indexing.
* **Google DeepMind** for pioneering Gemini model capabilities.
* **Pushkar Chhokar** for architecting and directing the Phase 5 DevMind Engine.
