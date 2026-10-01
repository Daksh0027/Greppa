const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function getStoredApiKey(): string {
  if (typeof window !== "undefined") {
    return localStorage.getItem("greppa_gemini_api_key") || "";
  }
  return "";
}

export function setStoredApiKey(key: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("greppa_gemini_api_key", key);
  }
}

function getHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const key = getStoredApiKey();
  if (key) {
    headers["X-Gemini-Api-Key"] = key;
  }
  return headers;
}

export async function fetchHealth() {
  const res = await fetch("http://localhost:8000/health");
  return res.json();
}

export async function listRepositories() {
  const res = await fetch(`${API_BASE}/repos`, { headers: getHeaders() });
  if (!res.ok) throw new Error("Failed to load repositories");
  return res.json();
}

export async function createRepository(data: { name: string; url_or_path: string; default_branch?: string }) {
  const res = await fetch(`${API_BASE}/repos`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ ...data, api_key: getStoredApiKey() || undefined }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create repository");
  }
  return res.json();
}

export async function createDemoRepository() {
  const res = await fetch(`${API_BASE}/repos/demo`, {
    method: "POST",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("Failed to create demo repository");
  return res.json();
}

export async function getRepository(repoId: number) {
  const res = await fetch(`${API_BASE}/repos/${repoId}`, { headers: getHeaders() });
  if (!res.ok) throw new Error("Failed to fetch repository");
  return res.json();
}

export async function syncRepository(repoId: number) {
  const res = await fetch(`${API_BASE}/repos/${repoId}/sync`, {
    method: "POST",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("Failed to trigger sync");
  return res.json();
}

export async function hybridSearch(repoId: number, query: string, topK: number = 10) {
  const res = await fetch(`${API_BASE}/repos/${repoId}/search`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({
      query,
      top_k: topK,
      expand_graph: true,
      api_key: getStoredApiKey() || undefined,
    }),
  });
  if (!res.ok) throw new Error("Search failed");
  return res.json();
}

export async function runAgentQuery(repoId: number, query: string, maxSteps: number = 6) {
  const res = await fetch(`${API_BASE}/repos/${repoId}/agent`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({
      query,
      max_steps: maxSteps,
      api_key: getStoredApiKey() || undefined,
    }),
  });
  if (!res.ok) throw new Error("Agent query failed");
  return res.json();
}

export async function getRepositoryGraph(repoId: number) {
  const res = await fetch(`${API_BASE}/repos/${repoId}/graph`, { headers: getHeaders() });
  if (!res.ok) throw new Error("Failed to fetch architecture graph");
  return res.json();
}

export async function listRepoFiles(repoId: number) {
  const res = await fetch(`${API_BASE}/repos/${repoId}/files`, { headers: getHeaders() });
  if (!res.ok) throw new Error("Failed to fetch file list");
  return res.json();
}

export async function getFileCode(repoId: number, path: string) {
  const res = await fetch(`${API_BASE}/repos/${repoId}/code?path=${encodeURIComponent(path)}`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch file code");
  return res.json();
}

export async function getGuidedTour(repoId: number) {
  const res = await fetch(`${API_BASE}/repos/${repoId}/tour`, { headers: getHeaders() });
  if (!res.ok) throw new Error("Failed to load guided tour");
  return res.json();
}

export async function matchGoodFirstIssue(repoId: number, title: string, description: string) {
  const res = await fetch(`${API_BASE}/repos/${repoId}/issues/match`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({
      title,
      description,
      api_key: getStoredApiKey() || undefined,
    }),
  });
  if (!res.ok) throw new Error("Failed to match issue");
  return res.json();
}
