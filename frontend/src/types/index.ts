export type RepoStatus = 'pending' | 'scanning' | 'parsing' | 'summarizing' | 'indexing' | 'ready' | 'failed';

export interface Repo {
  id: number;
  name: string;
  url_or_path: string;
  default_branch: string;
  status: RepoStatus;
  status_detail: string;
  stats: {
    total_files: number;
    total_symbols: number;
    total_lines: number;
  };
  repo_summary: string;
}

export interface FileNode {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
  importance?: number;
}

export interface Symbol {
  name: string;
  kind: 'function' | 'class' | 'variable' | 'interface' | 'module';
  start_line: number;
  end_line: number;
  snippet?: string;
  summary?: string;
}

export interface Citation {
  file_path: string;
  start_line: number;
  end_line: number;
  symbol?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  steps?: AgentStep[];
  createdAt: Date;
}

export interface AgentStep {
  step_number: number;
  thought: string;
  action: string;
  action_input: any;
  observation: string;
}

export interface TourStep {
  step_order: number;
  file_path: string;
  start_line: number;
  end_line: number;
  title: string;
  why_it_matters: string;
  body: string;
}

export interface Tour {
  id: number;
  repo_id: number;
  tour_type: 'big_picture' | 'feature_trace';
  title: string;
  description: string;
  steps: TourStep[];
}

export interface Issue {
  number: number;
  title: string;
  body: string;
  labels: string[];
  state: 'open' | 'closed';
  url: string;
  matched_files: {
    file_path: string;
    relevance_score: number;
    symbols: Symbol[];
  }[];
  contribution_plan: string;
  difficulty: 'easy' | 'medium' | 'hard' | string;
  estimated_time: string;
}

export interface ArchGraph {
  nodes: {
    id: string;
    label: string;
    kind: string;
    file_path: string;
    importance: number
  }[];
  edges: {
    source: string;
    target: string;
    edge_type: string;
    weight?: number
  }[];
}

export interface SearchHit {
  chunk_id: string;
  file_path: string;
  symbol_name?: string;
  start_line: number;
  end_line: number;
  header: string;
  content: string;
  summary: string;
  importance_score: number;
  score: number;
}

export interface SearchResponse {
  query: string;
  total_hits: number;
  hits: SearchHit[];
}
