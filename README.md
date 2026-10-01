# Greppa 🔍⚡

> **The core rule for large repos:** Never feed the whole codebase to a model. Build an index once, then retrieve only what each question needs.

Greppa is a large-repository code intelligence engine that combines AST symbol graph parsing, graph PageRank centrality scoring, hierarchical bottom-up summarization, pgvector hybrid search, and a multi-step agent retrieval loop.

---

## 🏗️ Architecture

```
                          ┌──────────────────────────┐
                          │     Git Repository       │
                          │   (Shallow / Local)      │
                          └─────────────┬────────────┘
                                        │
                    Respect .gitignore, skip binaries & lockfiles
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │   Tree-sitter AST Parser │
                          │ (Functions, Classes, AST)│
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │       Symbol Graph       │
                          │ (Defines, Calls, Imports)│
                          └──────┬────────────┬──────┘
                                 │            │
             PageRank Importance │            │ Bottom-Up Summarizer
                                 ▼            ▼
                         ┌──────────────┐   ┌─────────────────────────────┐
                         │ PageRank     │   │ Func ➔ File ➔ Folder ➔ Repo │
                         │ Centrality   │   │ Summaries (Cached)          │
                         └──────┬───────┘   └──────────────┬──────────────┘
                                │                          │
                                └───────────┬──────────────┘
                                            ▼
                       ┌──────────────────────────────────────────┐
                       │           PostgreSQL + pgvector          │
                       │ (HNSW Cosine Embeddings + tsvector FTS)  │
                       └────────────────────┬─────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               Query & Agent Pipeline                                   │
│                                                                                        │
│  1. Hybrid Search (Dense Cosine + Full-Text Keyword) ➔ Reciprocal Rank Fusion (RRF)    │
│  2. PageRank Prior Weighting (Boosts central architectural files)                       │
│  3. Graph Expansion (Pulls in callers, callees & parent classes)                       │
│  4. Token Budget Packer (Fits snippets strictly under token budget with line citations)│
│  5. Multi-Step Agent Loop (Searches, inspects symbols, follows calls, synthesizes)      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Features

1. **Intelligent AST Chunking & Symbol Graph**:
   - Chunks by symbol boundaries (functions, classes, methods), never by naive arbitrary line counts.
   - Preserves file paths, exact signatures, parent classes, and line numbers `[start_line - end_line]`.
   - Tracks `DEFINES`, `CALLS`, and `IMPORTS` relationships across modules.

2. **Graph PageRank Importance**:
   - Calculates PageRank scores across all files and symbols in the directed symbol graph.
   - Elevates central architecture entrypoints and high-fan-in abstractions.

3. **Hierarchical Bottom-Up Summarization**:
   - Bottom-up pipeline: Function $\rightarrow$ File $\rightarrow$ Folder $\rightarrow$ Repository.
   - Unchanged files are never re-summarized (cached by SHA-256 content hashes).

4. **Hybrid Search with Reciprocal Rank Fusion (RRF)**:
   - Fuses dense vector cosine similarity (Gemini `text-embedding-004` / pgvector) with PostgreSQL keyword full-text search.
   - Combines ranks via RRF weighted by PageRank importance.

5. **Graph Context Expansion & Token Budget Packing**:
   - For top hits, traverses 1-hop in the symbol graph to bring in immediate callers, callees, and parent class declarations.
   - Context packer enforces token budgets (e.g. 8,000 tokens) with citation anchors.

6. **Multi-Step Agent Reasoning Loop**:
   - Deep questions (*"How does authentication and token generation work end-to-end?"*) trigger an iterative agentic loop.
   - Shows the live step-by-step reasoning trace (`Thought` $\rightarrow$ `Action` $\rightarrow$ `Observation`) and synthesized answer with clickable file & line citations.

7. **Fast Incremental Invalidation**:
   - Computes SHA-256 hashes per file on sync.
   - Only invalidates and re-indexes modified files and their direct dependents in the symbol graph.

8. **Dynamic LLM Key Injection**:
   - Provider keys can be injected dynamically by the agent/UI or via `.env`.
   - Tested and optimized with **Google Gemini** (`gemini-2.0-flash` for bulk summaries, `gemini-2.0-pro` for agent reasoning, and `text-embedding-004` for vectors).
   - Includes local offline fallback for testing without API keys.

---

## 🛠️ Tech Stack

- **Frontend**: Next.js 14, Tailwind CSS, Monaco Editor (`@monaco-editor/react`), React Flow (`@xyflow/react`), Lucide icons.
- **Backend**: FastAPI (Python 3.14 compatible), SQLAlchemy, asyncpg/psycopg2, Tree-sitter, NetworkX.
- **Database**: PostgreSQL with `pgvector` extension (and local SQLite fallback for instant zero-install dev).
- **Queue & Storage**: Redis + background task workers.
- **LLM**: Google Gemini with dynamic per-request key override.

---

## ⚡ Quick Start

### Option A: Local Development (Instant Zero-Install Mode)

#### 1. Start the Backend
```bash
# In project root
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend/requirements.txt

# Start backend server
$env:PYTHONPATH="backend"
python backend/app/main.py
```
Backend will start on `http://localhost:8000` with interactive Swagger docs at `http://localhost:8000/docs`.

#### 2. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

### Option B: Docker Compose (Full Stack with Postgres + pgvector & Redis)

```bash
# Configure .env
cp backend/.env.example .env

# Run full stack
docker compose up --build
```
Services spun up:
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- PostgreSQL (pgvector): `localhost:5432`
- Redis: `localhost:6379`

---

## 🧪 Running Tests

```bash
$env:PYTHONPATH="backend"
pytest backend/tests/test_pipeline.py -v
```
Verifies AST parsing, symbol graph construction, PageRank computation, chunking, hybrid search, graph expansion, agent loop, and incremental dependency invalidation.
