import { GreppaApi, Repo } from './types';

export class HttpGreppaApi implements GreppaApi {
  private baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const apiKey = localStorage.getItem('greppa_gemini_api_key');
    const githubToken = localStorage.getItem('greppa_github_token');

    const headers = new Headers(options.headers);
    headers.set('Content-Type', 'application/json');
    if (apiKey) headers.set('X-Gemini-API-Key', apiKey);
    if (githubToken) headers.set('X-GitHub-Token', githubToken);

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `API request failed with status ${response.status}`);
    }

    return response.json();
  }

  async listRepos(): Promise<Repo[]> {
    return this.request<Repo[]>('/repos');
  }

  async createRepo(data: { name: string; url_or_path: string; default_branch?: string }): Promise<Repo> {
    return this.request<Repo>('/repos', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getRepo(id: string): Promise<Repo> {
    return this.request<Repo>(`/repos/${id}`);
  }

  async deleteRepo(id: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/repos/${id}`, {
      method: 'DELETE',
    });
  }

  async syncRepo(id: string): Promise<Repo> {
    return this.request<Repo>(`/repos/${id}/sync`, {
      method: 'POST',
    });
  }

  async search(repoId: string, query: string, options?: { top_k?: number; expand_graph?: boolean }): Promise<any> {
    return this.request<any>(`/repos/${repoId}/search`, {
      method: 'POST',
      body: JSON.stringify({ query, ...options }),
    });
  }

  async askAgent(repoId: string, query: string): Promise<any> {
    return this.request<any>(`/repos/${repoId}/agent`, {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  }

  async listTours(repoId: string): Promise<any> {
    return this.request<any>(`/tours/repo/${repoId}`);
  }

  async getTour(tourId: string): Promise<any> {
    return this.request<any>(`/tours/${tourId}`);
  }

  async generateTour(repoId: string, type: 'big_picture' | 'feature_trace', options?: { feature_query?: string }): Promise<any> {
    return this.request<any>(`/tours/repo/${repoId}/generate`, {
      method: 'POST',
      body: JSON.stringify({ tour_type: type, ...options }),
    });
  }

  async getGoodFirstIssues(repoId: string): Promise<any> {
    return this.request<any>(`/issues/repo/${repoId}/good-first-issues`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
  }

  async getSymbolGraph(repoId: string): Promise<any> {
    return this.request<any>(`/graph/repo/${repoId}`);
  }

  async getFileContent(repoId: string, path: string): Promise<any> {
    return this.request<any>(`/code/repo/${repoId}/file?path=${encodeURIComponent(path)}`);
  }
}
