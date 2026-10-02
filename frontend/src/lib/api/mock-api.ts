import { GreppaApi, Repo, SearchResponse, Tour, Issue, ArchGraph, Citation, AgentStep, StreamChunk } from './types';

export class MockGreppaApi implements GreppaApi {
  private async simulateLatency() {
    const delay = Math.random() * 500 + 200;
    await new Promise(resolve => setTimeout(resolve, delay));
  }

  async listRepos(): Promise<Repo[]> {
    await this.simulateLatency();
    return [
      {
        id: 1,
        name: 'agent-orchestrator',
        url_or_path: 'https://github.com/greppa/agent-orchestrator',
        default_branch: 'main',
        status: 'ready',
        status_detail: 'Index is active',
        stats: {
          total_files: 142,
          total_symbols: 1280,
          total_lines: 45000,
        },
        repo_summary: 'A high-performance agent orchestration framework designed for large-scale code intelligence tasks.',
      },
      {
        id: 2,
        name: 'sample-react-app',
        url_or_path: 'https://github.com/greppa/sample-react-app',
        default_branch: 'main',
        status: 'parsing',
        status_detail: 'Building AST graph...',
        stats: {
          total_files: 45,
          total_symbols: 300,
          total_lines: 8000,
        },
        repo_summary: 'A sample React application for testing Greppa ingestion.',
      }
    ];
  }

  async createRepo(data: { name: string; url_or_path: string; default_branch?: string }): Promise<Repo> {
    await this.simulateLatency();
    return {
      id: Math.floor(Math.random() * 1000),
      name: data.name,
      url_or_path: data.url_or_path,
      default_branch: data.default_branch || 'main',
      status: 'pending',
      status_detail: 'Queued for ingestion',
      stats: { total_files: 0, total_symbols: 0, total_lines: 0 },
      repo_summary: '',
    };
  }

  async getRepo(id: string): Promise<Repo> {
    await this.simulateLatency();
    const repos = await this.listRepos();
    const repo = repos.find(r => r.id === parseInt(id));
    if (!repo) throw new Error('Repo not found');
    return repo;
  }

  async deleteRepo(id: string): Promise<{ message: string }> {
    await this.simulateLatency();
    return { message: `Repository ${id} deleted successfully.` };
  }

  async syncRepo(id: string): Promise<Repo> {
    await this.simulateLatency();
    const repo = await this.getRepo(id);
    return { ...repo, status: 'indexing', status_detail: 'Syncing changes...' };
  }

  async search(repoId: string, query: string, options?: { top_k?: number; expand_graph?: boolean }): Promise<SearchResponse> {
    await this.simulateLatency();
    return {
      query,
      total_hits: 1,
      hits: [
        {
          chunk_id: 'chunk-1',
          file_path: 'src/orchestrator.ts',
          symbol_name: 'orchestrateTasks',
          start_line: 42,
          end_line: 85,
          header: 'async function orchestrateTasks(tasks: Task[]) {',
          content: 'async function orchestrateTasks(tasks: Task[]) {\n  // Implementation of task orchestration\n  for (const task of tasks) {\n    await execute(task);\n  }\n}',
          summary: 'Main entry point for coordinating agent tasks across the system.',
          importance_score: 9.5,
          score: 0.98,
        }
      ]
    };
  }

  async askAgent(repoId: string, query: string): Promise<{
    answer: string;
    citations: Citation[];
    steps: AgentStep[]
  }> {
    await this.simulateLatency();
    return {
      answer: `In the agent-orchestrator repo, the task scheduling is handled by the \`TaskScheduler\` class in \`src/scheduler.ts\`. It uses a priority queue to manage execution order.`,
      citations: [
        { file_path: 'src/scheduler.ts', start_line: 10, end_line: 50, symbol: 'TaskScheduler' }
      ],
      steps: [
        { step_number: 1, thought: 'Searching for scheduler implementation', action: 'hybrid_search', action_input: { query: 'scheduler' }, observation: 'Found TaskScheduler class in src/scheduler.ts' }
      ]
    };
  }

  async askAgentStream(repoId: string, query: string): Promise<AsyncIterable<StreamChunk>> {
    return {
      [Symbol.asyncIterator]() {
        const chunks: StreamChunk[] = [
          { type: 'step', step: { step_number: 1, thought: 'Analyzing the request...', action: 'hybrid_search', action_input: { query: query }, observation: 'Found relevant files in src/scheduler.ts and src/orchestrator.ts' } },
          { type: 'text', content: 'In the agent-orchestrator repo, ' },
          { type: 'text', content: 'the task scheduling is handled by the ' },
          { type: 'text', content: '`TaskScheduler` class ' },
          { type: 'citation', citation: { file_path: 'src/scheduler.ts', start_line: 10, end_line: 50, symbol: 'TaskScheduler' } },
          { type: 'text', content: ' in `src/scheduler.ts`. ' },
          { type: 'text', content: 'It uses a priority queue to manage execution order.' },
          { type: 'done' },
        ];

        let index = 0;
        return {
          async next() {
            if (index >= chunks.length) return { done: true, value: undefined };
            await new Promise(resolve => setTimeout(resolve, 100 + Math.random() * 200));
            return { done: false, value: chunks[index++] };
          },
        };
      },
    };
  }

  async listTours(repoId: string): Promise<Tour[]> {
    await this.simulateLatency();
    return [
      {
        id: 1,
        repo_id: parseInt(repoId),
        tour_type: 'big_picture',
        title: 'Big Picture Tour: agent-orchestrator',
        description: 'A high-level walkthrough of the orchestration logic.',
        steps: [
          {
            step_order: 1,
            file_path: 'src/index.ts',
            start_line: 1,
            end_line: 20,
            title: 'The Entry Point',
            why_it_matters: 'This is where the system boots up and initializes configurations.',
            body: 'The entry point sets up the environment and starts the main listener loop.',
          },
          {
            step_order: 2,
            file_path: 'src/orchestrator.ts',
            start_line: 40,
            end_line: 100,
            title: 'Task Coordination',
            why_it_matters: 'This is the heart of the system where agents are assigned to tasks.',
            body: 'The orchestrator manages the lifecycle of each agent task.',
          }
        ]
      }
    ];
  }

  async getTour(tourId: string): Promise<Tour> {
    await this.simulateLatency();
    const tours = await this.listTours('1');
    const tour = tours.find(t => t.id === parseInt(tourId));
    if (!tour) throw new Error('Tour not found');
    return tour;
  }

  async generateTour(repoId: string, type: 'big_picture' | 'feature_trace', options?: { feature_query?: string }): Promise<{ message: string }> {
    await this.simulateLatency();
    return { message: 'Tour generation started' };
  }

  async getGoodFirstIssues(repoId: string): Promise<Issue[]> {
    await this.simulateLatency();
    return [
      {
        number: 101,
        title: 'Improve error handling in TaskScheduler',
        body: 'The current error handling is too generic. We need more specific error types.',
        labels: ['good first issue', 'bug'],
        state: 'open',
        url: 'https://github.com/greppa/agent-orchestrator/issues/101',
        matched_files: [
          {
            file_path: 'src/scheduler.ts',
            relevance_score: 0.9,
            symbols: [{ name: 'scheduleTask', kind: 'function', start_line: 15, end_line: 30 }]
          }
        ],
        contribution_plan: '1. Define new error classes in src/errors.ts\n2. Update scheduleTask to throw these specific errors.',
        difficulty: 'easy',
        estimated_time: '2 hours',
      }
    ];
  }

  async getSymbolGraph(repoId: string): Promise<ArchGraph> {
    await this.simulateLatency();
    return {
      nodes: [
        { id: 'node-1', label: 'Orchestrator', kind: 'class', file_path: 'src/orchestrator.ts', importance: 10 },
        { id: 'node-2', label: 'Scheduler', kind: 'class', file_path: 'src/scheduler.ts', importance: 8 },
        { id: 'node-3', label: 'Agent', kind: 'class', file_path: 'src/agent.ts', importance: 7 },
      ],
      edges: [
        { source: 'node-1', target: 'node-2', edge_type: 'calls' },
        { source: 'node-2', target: 'node-3', edge_type: 'manages' },
      ]
    };
  }

  async getFileContent(repoId: string, path: string): Promise<{
    content: string;
    language: string;
    symbols: any[]
  }> {
    await this.simulateLatency();
    return {
      content: `// Content of ${path}\n\nexport function helloWorld() {\n  console.log("Hello Greppa!");\n}`,
      language: 'typescript',
      symbols: [
        { name: 'helloWorld', kind: 'function', start_line: 3, end_line: 5 }
      ]
    };
  }
} {
    await this.simulateLatency();
    return {
      id: Math.floor(Math.random() * 1000),
      name: data.name,
      url_or_path: data.url_or_path,
      default_branch: data.default_branch || 'main',
      status: 'pending',
      status_detail: 'Queued for ingestion',
      stats: { total_files: 0, total_symbols: 0, total_lines: 0 },
      repo_summary: '',
    };
  }

  async getRepo(id: string): Promise<Repo> {
    await this.simulateLatency();
    const repos = await this.listRepos();
    const repo = repos.find(r => r.id === parseInt(id));
    if (!repo) throw new Error('Repo not found');
    return repo;
  }

  async deleteRepo(id: string): Promise<{ message: string }> {
    await this.simulateLatency();
    return { message: `Repository ${id} deleted successfully.` };
  }

  async syncRepo(id: string): Promise<Repo> {
    await this.simulateLatency();
    const repo = await this.getRepo(id);
    return { ...repo, status: 'indexing', status_detail: 'Syncing changes...' };
  }

  async search(repoId: string, query: string, options?: { top_k?: number; expand_graph?: boolean }): Promise<SearchResponse> {
    await this.simulateLatency();
    return {
      query,
      total_hits: 1,
      hits: [
        {
          chunk_id: 'chunk-1',
          file_path: 'src/orchestrator.ts',
          symbol_name: 'orchestrateTasks',
          start_line: 42,
          end_line: 85,
          header: 'async function orchestrateTasks(tasks: Task[]) {',
          content: 'async function orchestrateTasks(tasks: Task[]) {\n  // Implementation of task orchestration\n  for (const task of tasks) {\n    await execute(task);\n  }\n}',
          summary: 'Main entry point for coordinating agent tasks across the system.',
          importance_score: 9.5,
          score: 0.98,
        }
      ]
    };
  }

  async askAgent(repoId: string, query: string): Promise<{
    answer: string;
    citations: any[];
    steps: any[]
  }> {
    await this.simulateLatency();
    return {
      answer: `In the agent-orchestrator repo, the task scheduling is handled by the \`TaskScheduler\` class in \`src/scheduler.ts\`. It uses a priority queue to manage execution order.`,
      citations: [
        { file_path: 'src/scheduler.ts', start_line: 10, end_line: 50, symbol: 'TaskScheduler' }
      ],
      steps: [
        { step_number: 1, thought: 'Searching for scheduler implementation', action: 'hybrid_search', action_input: { query: 'scheduler' }, observation: 'Found TaskScheduler class in src/scheduler.ts' }
      ]
    };
  }

  async listTours(repoId: string): Promise<Tour[]> {
    await this.simulateLatency();
    return [
      {
        id: 1,
        repo_id: parseInt(repoId),
        tour_type: 'big_picture',
        title: 'Big Picture Tour: agent-orchestrator',
        description: 'A high-level walkthrough of the orchestration logic.',
        steps: [
          {
            step_order: 1,
            file_path: 'src/index.ts',
            start_line: 1,
            end_line: 20,
            title: 'The Entry Point',
            why_it_matters: 'This is where the system boots up and initializes configurations.',
            body: 'The entry point sets up the environment and starts the main listener loop.',
          },
          {
            step_order: 2,
            file_path: 'src/orchestrator.ts',
            start_line: 40,
            end_line: 100,
            title: 'Task Coordination',
            why_it_matters: 'This is the heart of the system where agents are assigned to tasks.',
            body: 'The orchestrator manages the lifecycle of each agent task.',
          }
        ]
      }
    ];
  }

  async getTour(tourId: string): Promise<Tour> {
    await this.simulateLatency();
    const tours = await this.listTours('1');
    const tour = tours.find(t => t.id === parseInt(tourId));
    if (!tour) throw new Error('Tour not found');
    return tour;
  }

  async generateTour(repoId: string, type: 'big_picture' | 'feature_trace', options?: { feature_query?: string }): Promise<{ message: string }> {
    await this.simulateLatency();
    return { message: 'Tour generation started' };
  }

  async getGoodFirstIssues(repoId: string): Promise<Issue[]> {
    await this.simulateLatency();
    return [
      {
        number: 101,
        title: 'Improve error handling in TaskScheduler',
        body: 'The current error handling is too generic. We need more specific error types.',
        labels: ['good first issue', 'bug'],
        state: 'open',
        url: 'https://github.com/greppa/agent-orchestrator/issues/101',
        matched_files: [
          {
            file_path: 'src/scheduler.ts',
            relevance_score: 0.9,
            symbols: [{ name: 'scheduleTask', kind: 'function', start_line: 15, end_line: 30 }]
          }
        ],
        contribution_plan: '1. Define new error classes in src/errors.ts\n2. Update scheduleTask to throw these specific errors.',
        difficulty: 'easy',
        estimated_time: '2 hours',
      }
    ];
  }

  async getSymbolGraph(repoId: string): Promise<ArchGraph> {
    await this.simulateLatency();
    return {
      nodes: [
        { id: 'node-1', label: 'Orchestrator', kind: 'class', file_path: 'src/orchestrator.ts', importance: 10 },
        { id: 'node-2', label: 'Scheduler', kind: 'class', file_path: 'src/scheduler.ts', importance: 8 },
        { id: 'node-3', label: 'Agent', kind: 'class', file_path: 'src/agent.ts', importance: 7 },
      ],
      edges: [
        { source: 'node-1', target: 'node-2', edge_type: 'calls' },
        { source: 'node-2', target: 'node-3', edge_type: 'manages' },
      ]
    };
  }

  async getFileContent(repoId: string, path: string): Promise<{
    content: string;
    language: string;
    symbols: any[]
  }> {
    await this.simulateLatency();
    return {
      content: `// Content of ${path}\n\nexport function helloWorld() {\n  console.log("Hello Greppa!");\n}`,
      language: 'typescript',
      symbols: [
        { name: 'helloWorld', kind: 'function', start_line: 3, end_line: 5 }
      ]
    };
  }
}
