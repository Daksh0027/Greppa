import {
  Repo,
  SearchResponse,
  Tour,
  Issue,
  ArchGraph,
  Message,
  AgentStep,
  Citation
} from '../types';

export type StreamChunk =
  | { type: 'text'; content: string }
  | { type: 'citation'; citation: Citation }
  | { type: 'step'; step: AgentStep }
  | { type: 'done' };

export interface GreppaApi {
  // Repositories
  listRepos(): Promise<Repo[]>;
  createRepo(data: { name: string; url_or_path: string; default_branch?: string }): Promise<Repo>;
  getRepo(id: string): Promise<Repo>;
  deleteRepo(id: string): Promise<{ message: string }>;
  syncRepo(id: string): Promise<Repo>;

  // Search & Agent
  search(repoId: string, query: string, options?: { top_k?: number; expand_graph?: boolean }): Promise<SearchResponse>;
  askAgent(repoId: string, query: string): Promise<{
    answer: string;
    citations: any[];
    steps: AgentStep[]
  }>;
  askAgentStream(repoId: string, query: string): Promise<AsyncIterable<StreamChunk>>;

  // Tours
  listTours(repoId: string): Promise<Tour[]>;
  getTour(tourId: string): Promise<Tour>;
  generateTour(repoId: string, type: 'big_picture' | 'feature_trace', options?: { feature_query?: string }): Promise<{ message: string }>;

  // Issues
  getGoodFirstIssues(repoId: string): Promise<Issue[]>;

  // Code & Graph
  getSymbolGraph(repoId: string): Promise<ArchGraph>;
  getFileContent(repoId: string, path: string): Promise<{
    content: string;
    language: string;
    symbols: any[]
  }>;
}
