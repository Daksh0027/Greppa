# Greppa API Reference

Complete API documentation for Greppa's REST endpoints.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Greppa uses optional API key authentication via headers:

```http
X-Gemini-API-Key: your-gemini-api-key
X-GitHub-Token: your-github-token
```

## Rate Limiting

Different endpoint types have different rate limits:

| Tier | Limit | Endpoints |
|------|-------|-----------|
| General | 60/minute | List repos, get details |
| Search | 30/minute | Search, code browsing |
| LLM Operations | 10/minute | Tours, agent, issue matching |
| Ingestion | 5/hour | Create repo, sync |

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1609459200
```

---

## Repositories

### List Repositories

```http
GET /repos
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "my-repo",
    "url_or_path": "https://github.com/owner/repo",
    "default_branch": "main",
    "status": "ready",
    "status_detail": "Index is active",
    "stats": {
      "total_files": 150,
      "total_symbols": 1200,
      "total_lines": 50000
    },
    "repo_summary": "A web application for..."
  }
]
```

### Create Repository

```http
POST /repos
Content-Type: application/json

{
  "name": "my-repo",
  "url_or_path": "https://github.com/owner/repo",
  "default_branch": "main",
  "api_key": "optional-gemini-key"
}
```

**Response:** Repository object (202 Accepted - processing in background)

**Status Flow:**
1. `pending` - Queued for ingestion
2. `scanning` - Scanning file tree
3. `parsing` - Parsing AST and building graph
4. `summarizing` - Generating summaries
5. `indexing` - Creating embeddings
6. `ready` - Ready for queries
7. `failed` - Error occurred

### Get Repository

```http
GET /repos/{repo_id}
```

**Response:** Repository object

### Get Repository Cost

```http
GET /repos/{repo_id}/cost
```

**Response:**
```json
{
  "repo_id": 1,
  "total_cost_usd": 0.4523,
  "total_prompt_tokens": 125000,
  "total_completion_tokens": 15000,
  "total_embedding_tokens": 500000,
  "total_calls": 342,
  "cost_by_model": {
    "gemini-2.0-flash": 0.3200,
    "gemini-2.0-pro": 0.1323
  }
}
```

### Sync Repository

```http
POST /repos/{repo_id}/sync
```

Triggers incremental update for modified files.

**Response:** Repository object (202 Accepted)

### Delete Repository

```http
DELETE /repos/{repo_id}
```

**Response:**
```json
{
  "message": "Repository 'my-repo' deleted successfully."
}
```

---

## Search & Agent

### Hybrid Search

```http
POST /repos/{repo_id}/search
Content-Type: application/json
X-Gemini-API-Key: optional-key

{
  "query": "authentication token validation",
  "top_k": 12,
  "expand_graph": true,
  "token_budget": 6000
}
```

**Response:**
```json
{
  "query": "authentication token validation",
  "total_hits": 12,
  "hits": [
    {
      "chunk_id": 456,
      "file_path": "auth/validator.py",
      "symbol_name": "validate_token",
      "start_line": 45,
      "end_line": 68,
      "header": "def validate_token(token: str) -> bool:",
      "content": "def validate_token(token: str) -> bool:\n    ...",
      "summary": "Validates JWT tokens",
      "importance_score": 8.5,
      "score": 0.9234
    }
  ],
  "expanded_graph_contexts": [...]
}
```

### Agent Query

```http
POST /repos/{repo_id}/agent
Content-Type: application/json
X-Gemini-API-Key: required-key

{
  "query": "How does authentication work end-to-end?",
  "max_steps": 6,
  "token_budget": 8000
}
```

**Response:**
```json
{
  "answer": "Authentication in this system works through...",
  "citations": [
    {
      "file_path": "auth/handler.py",
      "start_line": 12,
      "end_line": 45,
      "symbol": "authenticate_user"
    }
  ],
  "steps": [
    {
      "step_number": 1,
      "thought": "Need to find authentication entry points",
      "action": "hybrid_search",
      "action_input": {"query": "authenticate"},
      "observation": "Found 3 authentication functions..."
    }
  ]
}
```

---

## Guided Tours

### List Tours

```http
GET /tours/repo/{repo_id}
```

**Response:**
```json
[
  {
    "id": 1,
    "repo_id": 1,
    "tour_type": "big_picture",
    "title": "Big Picture Tour: my-repo",
    "description": "An architectural walkthrough...",
    "steps": [...]
  }
]
```

### Get Tour

```http
GET /tours/{tour_id}
```

**Response:**
```json
{
  "id": 1,
  "repo_id": 1,
  "tour_type": "big_picture",
  "title": "Big Picture Tour: my-repo",
  "description": "An architectural walkthrough...",
  "steps": [
    {
      "step_order": 1,
      "file_path": "main.py",
      "start_line": 1,
      "end_line": 25,
      "title": "Application Entry Point",
      "why_it_matters": "This is where the application starts...",
      "body": "The main() function initializes the application..."
    }
  ]
}
```

### Generate Tour

```http
POST /tours/repo/{repo_id}/generate
Content-Type: application/json
X-Gemini-API-Key: required-key

{
  "tour_type": "big_picture",
  "title": "Optional Custom Title",
  "max_steps": 12
}
```

**For Feature Trace:**
```json
{
  "tour_type": "feature_trace",
  "feature_query": "How does authentication work?",
  "max_steps": 8
}
```

**Response:**
```json
{
  "message": "Tour generation started",
  "repo_id": 1,
  "tour_type": "big_picture"
}
```

Tour generation happens in the background. Poll `GET /tours/repo/{repo_id}` to see when it's complete.

### Delete Tour

```http
DELETE /tours/{tour_id}
```

**Response:**
```json
{
  "message": "Tour 'Big Picture Tour' deleted successfully"
}
```

---

## GitHub Integration

### Get Good First Issues

```http
POST /issues/repo/{repo_id}/good-first-issues
Content-Type: application/json
X-GitHub-Token: optional-token
X-Gemini-API-Key: required-key

{
  "labels": ["good first issue", "help wanted"],
  "max_count": 20
}
```

**Response:**
```json
[
  {
    "number": 123,
    "title": "Add validation for user input",
    "body": "We need to add validation...",
    "labels": ["good first issue", "enhancement"],
    "state": "open",
    "url": "https://github.com/owner/repo/issues/123",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-16T14:20:00Z",
    "comments": 3,
    "matched_files": [
      {
        "file_path": "validators/input_validator.py",
        "relevance_score": 0.89,
        "symbols": [
          {
            "name": "validate_input",
            "line_range": "45-68",
            "snippet": "def validate_input(data)..."
          }
        ]
      }
    ],
    "contribution_plan": "To implement this feature:\n1. Add validation logic...",
    "difficulty": "Beginner",
    "estimated_time": "1-2 hours"
  }
]
```

### Match Single Issue

```http
GET /issues/repo/{repo_id}/issue/{issue_number}
X-GitHub-Token: optional-token
X-Gemini-API-Key: required-key
```

**Response:** Single issue object (same format as above)

### Get GitHub Repository Info

```http
GET /issues/repo/{repo_id}/github-info
X-GitHub-Token: optional-token
```

**Response:**
```json
{
  "full_name": "owner/repo",
  "description": "A web application for...",
  "stars": 1234,
  "forks": 56,
  "open_issues": 23,
  "language": "Python",
  "has_contributing": true,
  "contributing_excerpt": "# Contributing Guide\n\nTo contribute...",
  "test_commands": ["pytest tests/", "npm test"],
  "html_url": "https://github.com/owner/repo"
}
```

---

## Graph Visualization

### Get Symbol Graph

```http
GET /graph/repo/{repo_id}?max_nodes=100&max_edges=200
```

**Query Parameters:**
- `max_nodes` (optional): Maximum nodes to return (default: 100)
- `max_edges` (optional): Maximum edges to return (default: 200)

**Response:**
```json
{
  "nodes": [
    {
      "id": "sym:main.py:main",
      "label": "main",
      "kind": "function",
      "file_path": "main.py",
      "importance": 10.0
    }
  ],
  "edges": [
    {
      "source": "sym:main.py:main",
      "target": "sym:utils.py:process",
      "edge_type": "calls"
    }
  ]
}
```

---

## Code Browsing

### Get File Content

```http
GET /code/repo/{repo_id}/file?path=src/main.py
```

**Query Parameters:**
- `path` (required): File path relative to repository root

**Response:**
```json
{
  "file_path": "src/main.py",
  "content": "def main():\n    ...",
  "language": "python",
  "line_count": 150,
  "symbols": [
    {
      "name": "main",
      "kind": "function",
      "start_line": 1,
      "end_line": 25
    }
  ]
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "detail": "Additional context (optional)"
}
```

### Common Error Codes

- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Missing or invalid API key
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### Rate Limit Error

```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please slow down and try again later.",
  "detail": "30 per 1 minute"
}
```

---

## Pagination

List endpoints support pagination:

```http
GET /repos?skip=0&limit=20
```

**Query Parameters:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 20, max: 100)

---

## Webhooks (Future)

Coming soon: GitHub webhook support for automatic repository updates.

---

## SDK Examples

### Python

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"
GEMINI_KEY = "your-key"

# Create repository
response = requests.post(
    f"{BASE_URL}/repos",
    json={
        "name": "my-repo",
        "url_or_path": "https://github.com/owner/repo"
    },
    headers={"X-Gemini-API-Key": GEMINI_KEY}
)
repo = response.json()

# Search
response = requests.post(
    f"{BASE_URL}/repos/{repo['id']}/search",
    json={"query": "authentication", "top_k": 10},
    headers={"X-Gemini-API-Key": GEMINI_KEY}
)
hits = response.json()["hits"]

# Generate tour
response = requests.post(
    f"{BASE_URL}/tours/repo/{repo['id']}/generate",
    json={"tour_type": "big_picture", "max_steps": 10},
    headers={"X-Gemini-API-Key": GEMINI_KEY}
)
```

### JavaScript/TypeScript

```typescript
const BASE_URL = "http://localhost:8000/api/v1";
const GEMINI_KEY = "your-key";

// Create repository
const repo = await fetch(`${BASE_URL}/repos`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-Gemini-API-Key": GEMINI_KEY,
  },
  body: JSON.stringify({
    name: "my-repo",
    url_or_path: "https://github.com/owner/repo",
  }),
}).then(r => r.json());

// Search
const searchResults = await fetch(
  `${BASE_URL}/repos/${repo.id}/search`,
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Gemini-API-Key": GEMINI_KEY,
    },
    body: JSON.stringify({
      query: "authentication",
      top_k: 10,
    }),
  }
).then(r => r.json());
```

---

## Interactive API Documentation

Visit `http://localhost:8000/docs` for interactive Swagger UI documentation where you can test all endpoints directly.

---

**Last Updated:** 2026-10-01
