# DevMind Architecture Design & Multi-Agent Workflow

This document details the system design, request lifecycle, folder structures, REST APIs, and future multi-agent orchestration patterns for **DevMind**.

---

## 1. Overall Architecture

DevMind is designed as a decoupled, single-page application consisting of:
- **React Frontend**: A Vite-powered React client built with TypeScript and Tailwind CSS. It manages user selections, file uploads, and displays multi-agent status progressions and markdown reports.
- **FastAPI Backend**: A lightweight, high-performance Python ASGI backend that exposes REST endpoints and drives code checkouts, scanners, and chunking engines asynchronously.

```
┌────────────────────────────────────────────────────────┐
│                   React Frontend                       │
│  ┌───────────────────────┐   ┌──────────────────────┐  │
│  │   AnalysisContext     │──>│    Dashboard Page    │  │
│  │   (State Orchestrator)│   │  (Agent Monitor UI)  │  │
│  └───────────┬───────────┘   └──────────────────────┘  │
└──────────────│─────────────────────────────────────────┘
               │ (Axios HTTP Calls)
               ▼
┌────────────────────────────────────────────────────────┐
│                   FastAPI Backend                      │
│  ┌──────────────────────────────────────────────────┐  │
│  │                   REST Router                    │  │
│  │  (/review, /upload, /status/{id}, /result/{id})  │  │
│  └───────────────────┬──────────────────────────────┘  │
│                      │ (BackgroundTasks Thread Pool)   │
│                      ▼                                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │                  JobService                      │  │
│  │  (In-Memory Registry & Pipeline Orchestrator)    │  │
│  └─────┬─────────────┬─────────────┬────────────────┘  │
│        │             │             │                   │
│        ▼             ▼             ▼                   │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐             │
│  │Repository │ │  Scanner  │ │   Chunk   │             │
│  │  Service  │ │  Service  │ │  Service  │             │
│  │(GitPython)│ │ (Metadata)│ │ (Parsing) │             │
│  └───────────┘ └───────────┘ └───────────┘             │
└────────────────────────────────────────────────────────┘
```

---

## 2. Request Lifecycle

The system handles both GitHub URL checkout requests and ZIP file uploads. The workflow follows this lifecycle:

1. **User Action**: The user inputs a GitHub URL or drops a ZIP file, selects a task (e.g. `Review Repository`), and clicks **Start Analysis**.
2. **Registration (HTTP Post)**:
   - The React client fires a POST request to `/review` (or `/upload` as multipart form data).
   - The FastAPI backend validates schemas, generates a unique UUID `job_id`, and stores the initial job state (status=`running`, progress=`5`, stage=`Initializing`) in memory.
   - The route handler queues `job_service.run_analysis_pipeline` in the ASGI server's background thread pool and immediately returns `201 Created` with the `job_id`.
3. **Background Execution**:
   - **Phase 1: Clone/Extract** (Progress 15%): `repository_service` downloads the remote GitHub branch (depth=1) or unpacks the uploaded ZIP file into `backend/temp/{job_id}`.
   - **Phase 2: Metadata Scan** (Progress 45%): `scanner_service` walks the workspace directory structure recursively. It extracts key files, folder totals, package managers, and parses dependencies from config manifests.
   - **Phase 3: Code Chunking** (Progress 75%): `chunk_service` reads supported code files and partitions text into 500-1000 character windows, caching them in memory mapped under the `job_id`.
   - **Phase 4: Completion** (Progress 100%): The pipeline compiles a markdown report detailing repository metrics, sets the job status to `completed`, and purges the temporary folder.
4. **Client Polling**:
   - The React frontend polls `GET /status/{job_id}` at 1-second intervals.
   - The client virtualizes the simple `progress` percentage and active `stage` messages into the 4-agent status cards (`planner`, `retriever`, `reviewer`, `critic`) visible in the UI.
   - Once progress reaches `100%`, the client queries `GET /result/{job_id}` to fetch the completed report and display it in the output console.

---

## 3. Workspace Folder Structure

The codebase is organized as follows:

```
DevMind/
├── backend/                  # Python FastAPI Backend Project
│   ├── app/                  # Application Core Package
│   │   ├── api/              # Route controllers & dependencies
│   │   │   ├── dependencies.py
│   │   │   └── routes.py
│   │   ├── core/             # Base configurations & logger
│   │   │   ├── config.py
│   │   │   ├── constants.py
│   │   │   └── logger.py
│   │   ├── models/           # Pydantic schemas (Request / Response)
│   │   │   ├── request.py
│   │   │   ├── response.py
│   │   │   └── job.py
│   │   ├── services/         # Core business logic handlers
│   │   │   ├── chunk_service.py
│   │   │   ├── job_service.py
│   │   │   ├── repository_service.py
│   │   │   └── scanner_service.py
│   │   ├── utils/            # General helpers (Git, File systems)
│   │   │   ├── file.py
│   │   │   ├── git.py
│   │   │   └── helpers.py
│   │   └── main.py           # Application entrypoint
│   ├── temp/                 # Temporary workspace checkout area (ignored by Git)
│   └── tests/                # Pytest unit testing suite
├── src/                      # React Frontend Source Project
│   ├── assets/               # Image/SVG assets
│   ├── components/           # Reusable UI components
│   │   ├── Navbar.tsx
│   │   ├── OutputPanel.tsx
│   │   ├── PrimaryButton.tsx
│   │   ├── RepositoryCard.tsx
│   │   ├── StatusCard.tsx
│   │   └── TaskSelector.tsx
│   ├── context/              # Context Providers (AnalysisContext)
│   ├── hooks/                # React custom hooks (useAnalysis)
│   ├── layouts/              # UI structural wrappers (MainLayout)
│   ├── pages/                # Page views (Dashboard)
│   ├── services/             # Axios client configuration (api.ts)
│   ├── types/                # TypeScript interface type files
│   └── index.css             # Tailwind CSS & global styles
├── index.html                # Vite entry point
├── package.json              # NPM package manifest
├── postcss.config.js         # PostCSS configuration (Tailwind integration)
├── tailwind.config.js        # Tailwind v3 layout configuration (if needed)
└── vite.config.ts            # Vite compile settings
```

---

## 4. REST API Endpoints

| Method | Endpoint | Description | Payload Shape | Response Shape |
| :--- | :--- | :--- | :--- | :--- |
| **POST** | `/review` | Submits a public repository URL to clone and analyze | `{"repo_url": "...", "task": "..."}` | `{"job_id": "..."}` |
| **POST** | `/upload` | Uploads a ZIP file containing source code files | Multipart `file` & `task` form-data | `{"job_id": "..."}` |
| **GET** | `/status/{job_id}` | Retrieves the running status, progress, and stage | N/A | `{"status": "...", "progress": 35, "stage": "..."}` |
| **GET** | `/result/{job_id}` | Retrieves the compiled markdown analysis report | N/A | `{"status": "completed", "result": "..."}` |
| **GET** | `/` | Base health-check endpoint | N/A | `{"status": "healthy", "service": "DevMind"}` |

---

## 5. Data Flow Mapping

The data passes through these structural shapes during the review workflow:

```
[GitHub Repo URL] ──> ReviewRequest (repo_url, task)
                             │
                             ▼
                    AnalysisJob Schema
             ┌──────────────────────────────┐
             │ id: "job_uuid_string"        │
             │ progress: 45                 │
             │ stage: "Scanning Codebase"   │
             │ result_text: Optional[str]   │
             └──────────────┬───────────────┘
                            │
              (Client Status Polling)
                            ▼
              StatusResponse (status, progress, stage)
                            │
               (Virtual UI Mapping in api.ts)
                            ▼
                    MultiAgentStatus
             ┌──────────────────────────────┐
             │ planner:   {status, message} │
             │ retriever: {status, message} │
             │ reviewer:  {status, message} │
             │ critic:    {status, message} │
             └──────────────────────────────┘
```

---

## 6. Future Multi-Agent Workflow (Phase 2 Blueprint)

When transitioning to RAG and LLMs in Phase 2, the sequential background pipeline will be replaced with an **event-driven agent supervisor pattern**:

```
                       ┌──────────────────┐
                       │ Agent Supervisor │
                       └────────┬─────────┘
                                │
        ┌───────────────┬───────┴───────┬───────────────┐
        ▼               ▼               ▼               ▼
 ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
 │   Planner   │ │  Retriever  │ │  Reviewer   │ │   Critic    │
 │    Agent    │ │    Agent    │ │    Agent    │ │    Agent    │
 └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### Agent Roles & Workflows

1. **Planner Agent**:
   - Takes the user request (`task` = `review`, `explain`, `tests`, `bugs`) and parses the scanned `RepositoryMetadata` (framework, language, files list).
   - Generates a custom task blueprint defining *which modules* should be extracted and *which queries* should be executed.
2. **Retriever Agent**:
   - Implements a local semantic search engine (e.g. FAISS, ChromaDB, or BM25 keyword matching) using the caches in `chunk_service`.
   - Embeds code chunks and pulls relevant code fragments matching the Planner's blueprint questions.
3. **Reviewer Agent**:
   - Consumes the retrieved context blocks and evaluates the code files.
   - Interacts with an LLM (e.g., Gemini Pro) to run static analyses, generate tests, explain architecture, or highlight bugs based on the user's task.
4. **Critic Agent**:
   - Reviews the Reviewer Agent's output for logic correctness, completeness, and styling guidelines.
   - Provides corrective feedback back to the Reviewer Agent if details are missing, or signs off on the final report to compile the Markdown findings.
