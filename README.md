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

9. **🎯 Guided Code Tours** *(NEW)*:
   - Automatically generates "read the code in this order" walkthroughs
   - **Big Picture Tours**: Start from entry points and traverse call graph
   - **Feature Trace Tours**: Custom tours based on specific questions (e.g., "How does auth work?")
   - LLM-generated step explanations with "why it matters" context

10. **🔧 GitHub Issue Matching** *(NEW)*:
    - Fetches "good first issue" labels from GitHub repositories
    - Matches issues to relevant code files using hybrid search
    - Generates AI-powered contribution plans with difficulty estimates
    - Extracts test commands from CONTRIBUTING.md

11. **🔒 Production-Ready Security** *(NEW)*:
    - Rate limiting with different tiers (search: 30/min, LLM ops: 10/min, ingestion: 5/hour)
    - Input sanitization and validation to prevent injection attacks
    - URL validation to prevent SSRF attacks
    - Prompt injection detection
    - Security headers and request logging

12. **📊 Observability & Cost Tracking** *(NEW)*:
    - Tracks every LLM call (model, tokens, latency, cost)
    - Real-time cost estimation per repository
    - Performance monitoring for all operations
    - Structured logging for debugging
    - Cost breakdown by model type

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


---

## 📚 API Documentation

### Core Endpoints

#### Repositories
- `GET /api/v1/repos` - List all repositories
- `POST /api/v1/repos` - Create and index a new repository
- `GET /api/v1/repos/{repo_id}` - Get repository details
- `GET /api/v1/repos/{repo_id}/cost` - Get LLM cost tracking for repo
- `POST /api/v1/repos/{repo_id}/sync` - Trigger incremental update
- `DELETE /api/v1/repos/{repo_id}` - Delete repository

#### Search & Agent
- `POST /api/v1/repos/{repo_id}/search` - Hybrid search with graph expansion
- `POST /api/v1/repos/{repo_id}/agent` - Multi-step agent query with reasoning

#### Guided Tours *(NEW)*
- `GET /api/v1/tours/repo/{repo_id}` - List all tours for a repository
- `GET /api/v1/tours/{tour_id}` - Get tour details with all steps
- `POST /api/v1/tours/repo/{repo_id}/generate` - Generate a new tour
  - Body: `{"tour_type": "big_picture", "max_steps": 12}`
  - Or: `{"tour_type": "feature_trace", "feature_query": "How does auth work?", "max_steps": 8}`
- `DELETE /api/v1/tours/{tour_id}` - Delete a tour

#### GitHub Integration *(NEW)*
- `POST /api/v1/issues/repo/{repo_id}/good-first-issues` - Fetch and match good first issues
  - Body: `{"labels": ["good first issue", "help wanted"], "max_count": 20}`
  - Returns: Issues with matched files, contribution plans, difficulty estimates
- `GET /api/v1/issues/repo/{repo_id}/issue/{issue_number}` - Match specific issue to code
- `GET /api/v1/issues/repo/{repo_id}/github-info` - Get repo info and contributing guidelines

#### Graph Visualization
- `GET /api/v1/graph/repo/{repo_id}` - Get symbol graph for visualization

#### Code Browsing
- `GET /api/v1/code/repo/{repo_id}/file` - Get file content with highlighting

### Request Headers

- `X-Gemini-API-Key`: Optional Gemini API key for LLM operations
- `X-GitHub-Token`: Optional GitHub personal access token (for higher rate limits and private repos)

### Rate Limits

- **General API**: 60 requests/minute
- **Search**: 30 requests/minute
- **LLM Operations** (tours, issue matching, agent): 10 requests/minute
- **Ingestion**: 5 requests/hour

---

## 🧪 Development

### Setup Development Environment

```bash
cd backend

# Install dependencies including dev tools
pip install -r requirements.txt

# Install pre-commit hooks
make pre-commit

# Run database migrations
make migrate
```

### Available Make Commands

```bash
make help          # Show all available commands
make install       # Install dependencies
make lint          # Run Ruff linter
make format        # Format code with Ruff
make test          # Run pytest tests
make clean         # Remove cache files
make run           # Start development server
make migrate       # Run database migrations
make check-all     # Run linting and tests
```

### Running Tests

```bash
# Run all tests
cd backend
PYTHONPATH=. pytest tests/ -v

# Run specific test file
PYTHONPATH=. pytest tests/test_tours.py -v

# Run with coverage
PYTHONPATH=. pytest tests/ --cov=app --cov-report=html
```

### Code Quality

The project uses:
- **Ruff** for linting and formatting
- **MyPy** for type checking (optional)
- **Pre-commit hooks** for automatic checks
- **GitHub Actions CI** for automated testing

To run code quality checks:

```bash
# Lint code
ruff check backend/

# Format code
ruff format backend/

# Type check (optional)
mypy backend/app --ignore-missing-imports
```

---

## 🔐 Security Best Practices

### API Key Management

Never commit API keys to version control. Use environment variables or headers:

```bash
# Set in environment
export GEMINI_API_KEY="your-key-here"

# Or pass in request header
curl -H "X-Gemini-API-Key: your-key" http://localhost:8000/api/v1/repos
```

### Production Deployment Checklist

- [ ] Set strong database passwords
- [ ] Enable HTTPS/TLS
- [ ] Configure rate limiting thresholds
- [ ] Set up monitoring and alerting
- [ ] Enable database backups
- [ ] Review security headers configuration
- [ ] Restrict CORS origins to your domains
- [ ] Set up log aggregation
- [ ] Configure firewall rules
- [ ] Use secrets management (e.g., AWS Secrets Manager, HashiCorp Vault)

### Security Features

- **Input Validation**: All user inputs are sanitized
- **Rate Limiting**: Prevents abuse and controls costs
- **SSRF Protection**: URL validation for repository cloning
- **Prompt Injection Detection**: Monitors for malicious prompts
- **Security Headers**: HSTS, X-Frame-Options, CSP
- **Request Logging**: All requests logged for audit

---

## 📊 Cost Estimation

### LLM Costs (Gemini Pricing)

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Use Case |
|-------|----------------------|------------------------|----------|
| gemini-2.0-flash | $0.075 | $0.30 | Summaries, embeddings |
| gemini-2.0-pro | $1.25 | $5.00 | Agent reasoning, tours |
| text-embedding-004 | Free | Free | Vector embeddings |

### Typical Repository Costs

**Small Repository** (5k LOC, 50 files):
- Ingestion: ~$0.02
- 10 searches: ~$0.01
- 1 tour generation: ~$0.05
- **Total: ~$0.08**

**Medium Repository** (50k LOC, 500 files):
- Ingestion: ~$0.20
- 100 searches: ~$0.10
- 5 tours: ~$0.25
- **Total: ~$0.55**

**Large Repository** (500k LOC, 5000 files):
- Ingestion: ~$2.00
- 1000 searches: ~$1.00
- 10 tours: ~$0.50
- **Total: ~$3.50**

*Note: Costs are estimates. Track actual costs using `/api/v1/repos/{repo_id}/cost` endpoint.*

---

## 🗄️ Database Schema

### Core Tables

- **repositories**: Repository metadata and status
- **repo_versions**: Git commit tracking
- **files**: Indexed files with importance scores
- **symbols**: Functions, classes, methods with PageRank scores
- **symbol_edges**: Call graph relationships
- **chunk_embeddings**: Vector embeddings for search
- **folder_summaries**: Hierarchical summaries
- **jobs**: Background job tracking

### New Tables

- **tours**: Guided code tour metadata *(NEW)*
- **tour_steps**: Individual tour steps with explanations *(NEW)*
- **cost_tracking**: LLM API call costs and token usage *(NEW)*
- **chat_sessions**: Agent conversation history
- **chat_messages**: Individual messages with citations

### Migrations

Database migrations are managed with Alembic:

```bash
# Run migrations
cd backend
PYTHONPATH=. alembic upgrade head

# Create new migration
PYTHONPATH=. alembic revision --autogenerate -m "Description"

# Check migration status
PYTHONPATH=. alembic current
```

---

## 🎯 Use Cases

### 1. Onboarding New Developers

```bash
# Generate a big picture tour
POST /api/v1/tours/repo/1/generate
{
  "tour_type": "big_picture",
  "max_steps": 12
}

# Walk through the tour to understand architecture
GET /api/v1/tours/{tour_id}
```

### 2. Finding Good First Issues

```bash
# Fetch and match issues
POST /api/v1/issues/repo/1/good-first-issues
{
  "labels": ["good first issue"],
  "max_count": 20
}

# Returns issues with:
# - Matched files
# - Contribution plans
# - Difficulty estimates
# - Time estimates
```

### 3. Understanding a Feature

```bash
# Generate a feature trace tour
POST /api/v1/tours/repo/1/generate
{
  "tour_type": "feature_trace",
  "feature_query": "How does authentication work?",
  "max_steps": 8
}
```

### 4. Cost Monitoring

```bash
# Check repository LLM costs
GET /api/v1/repos/1/cost

# Returns:
# - Total cost in USD
# - Token usage breakdown
# - Cost by model
# - Number of API calls
```

---

## 🤝 Contributing

We welcome contributions! Please see our development setup above.

### Contribution Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Install pre-commit hooks (`make pre-commit`)
4. Make your changes and add tests
5. Run linting and tests (`make check-all`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings to public functions
- Write tests for new features
- Keep functions focused and modular

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- Tree-sitter for AST parsing
- Google Gemini for LLM capabilities
- pgvector for vector search
- FastAPI for the backend framework
- Next.js for the frontend framework

---

## 📧 Support

For questions, issues, or feature requests, please open an issue on GitHub.

---

**Built with ❤️ for developers who work with large codebases**
