'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  FileText,
  Layers,
  GitBranch,
  ExternalLink,
  RefreshCcw,
  ArrowRight,
  PlayCircle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { api } from '@/lib/api/client';
import GraphView from '@/components/features/arch-graph/GraphView';
import { Repo } from '@/types';

export default function OverviewPage({ params }: { params: { repoId: string } }) {
  const { repoId } = params;
  const [selectedNode, setSelectedNode] = useState<any>(null);

  const { data: repo, isLoading, error, refetch } = useQuery({
    queryKey: ['repo', repoId],
    queryFn: () => api.getRepo(repoId),
  });

  const { data: graphData } = useQuery({
    queryKey: ['graph', repoId],
    queryFn: () => api.getSymbolGraph(repoId),
    enabled: !!repo,
  });

  if (isLoading) return <div className="p-12 flex justify-center"><Loader2 className="w-8 h-8 animate-spin text-teal-500" /></div>;
  if (error || !repo) return <div className="p-12 text-center text-red-500">Error loading repository overview.</div>;

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-4xl font-bold text-white">{repo.name}</h1>
            <Button variant="outline" size="sm" asChild className="h-8 text-xs border-zinc-800 text-zinc-400 hover:bg-zinc-900">
              <a href={`https://github.com/${repo.url_or_path}`} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="w-3 h-3 mr-1" /> GitHub
              </a>
            </Button>
          </div>
          <div className="flex items-center gap-4 text-sm text-zinc-500">
            <span className="flex items-center gap-1"><GitBranch className="w-3 h-3" /> {repo.default_branch}</span>
            <span>Last indexed: {new Date().toLocaleDateString()}</span>
          </div>
        </div>
        <Button
          onClick={() => refetch()}
          variant="secondary"
          className="bg-zinc-900 text-zinc-300 border-zinc-800 hover:bg-zinc-800 gap-2"
        >
          <RefreshCcw className="w-4 h-4" />
          Refresh Index
        </Button>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 bg-zinc-900 border-zinc-800 shadow-xl">
          <div className="flex items-center gap-3 mb-2 text-zinc-400">
            <FileText className="w-5 h-5 text-teal-500" />
            <span className="text-sm font-medium">Total Files</span>
          </div>
          <div className="text-3xl font-bold text-white font-mono">{repo.stats.total_files}</div>
        </Card>
        <Card className="p-6 bg-zinc-900 border-zinc-800 shadow-xl">
          <div className="flex items-center gap-3 mb-2 text-zinc-400">
            <Layers className="w-5 h-5 text-blue-500" />
            <span className="text-sm font-medium">Total Symbols</span>
          </div>
          <div className="text-3xl font-bold text-white font-mono">{repo.stats.total_symbols}</div>
        </Card>
        <Card className="p-6 bg-zinc-900 border-zinc-800 shadow-xl">
          <div className="flex items-center gap-3 mb-2 text-zinc-400">
            <Code2 className="w-5 h-5 text-purple-500" />
            <span className="text-sm font-medium">Lines of Code</span>
          </div>
          <div className="text-3xl font-bold text-white font-mono">{repo.stats.total_lines.toLocaleString()}</div>
        </Card>
      </div>

      {/* Summary Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <section>
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5 text-teal-500" />
              What this project does
            </h2>
            <p className="text-zinc-400 leading-relaxed text-lg">
              {repo.repo_summary}
            </p>
          </section>

          <section className="h-[600px] relative">
            <h2 className="text-xl font-semibold text-white mb-4">Architecture Map</h2>
            <GraphView
              data={graphData || { nodes: [], edges: [] }}
              onNodeClick={(node) => setSelectedNode(node)}
            />
          </section>
        </div>

        <div className="space-y-8">
          {/* Node Details Panel */}
          <section className="p-6 rounded-3xl bg-zinc-900 border border-zinc-800 sticky top-6">
            {selectedNode ? (
              <div className="space-y-4">
                <div className="flex justify-between items-start">
                  <h3 className="text-xl font-bold text-white">{selectedNode.label}</h3>
                  <span className="px-2 py-1 rounded-md bg-teal-500/10 text-teal-500 text-[10px] font-bold uppercase">
                    {selectedNode.kind}
                  </span>
                </div>
                <p className="text-sm text-zinc-400 font-mono bg-zinc-950 p-2 rounded border border-zinc-800 truncate">
                  {selectedNode.file_path}
                </p>
                <p className="text-sm text-zinc-300 leading-relaxed">
                  This module is responsible for managing the core orchestration loop and coordinating state between agent tasks.
                </p>
                <div className="flex flex-col gap-2 pt-4">
                  <Button asChild className="w-full bg-teal-600 hover:bg-teal-500 text-white rounded-xl">
                    <Link href={`/repo/${repoId}/explore?file=${selectedNode.file_path}`}>
                      Open in Explorer
                    </Link>
                  </Button>
                  <Button variant="outline" asChild className="w-full border-zinc-800 text-zinc-300 rounded-xl">
                    <Link href={`/repo/${repoId}/chat?query=Tell me more about ${selectedNode.label}`}>
                      Ask about this
                    </Link>
                  </Button>
                </div>
              </div>
            ) : (
              <div className="text-center py-12">
                <Map className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
                <p className="text-zinc-500 text-sm">Select a node in the architecture map to see details</p>
              </div>
            )}
          </section>

          {/* CTA Card */}
          <section className="p-6 rounded-3xl bg-gradient-to-br from-teal-600 to-teal-800 text-white shadow-xl">
            <h3 className="text-xl font-bold mb-2">Ready to dive in?</h3>
            <p className="text-teal-100 text-sm mb-6 opacity-90">
              Start a guided tour to understand how this codebase is structured.
            </p>
            <Button
              asChild
              className="w-full bg-white text-teal-800 hover:bg-zinc-100 font-bold rounded-xl"
            >
              <Link href={`/repo/${repoId}/tour`}>
                Start Guided Tour <ArrowRight className="ml-2 w-4 h-4" />
              </Link>
            </Button>
          </section>
        </div>
      </div>
    </div>
  );
}

function Loader2({ className }: { className?: string }) {
  return <div className={className} />;
}

function Code2({ className }: { className?: string }) {
  return <div className={className} />;
}

function Zap({ className }: { className?: string }) {
  return <div className={className} />;
}
