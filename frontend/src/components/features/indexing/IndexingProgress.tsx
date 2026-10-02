'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, Circle, Loader2, RefreshCcw, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { api } from '@/lib/api/client';
import { Repo, RepoStatus } from '@/types';
import { useRouter } from 'next/navigation';

type IndexingStage = {
  id: RepoStatus;
  label: string;
  order: number;
};

const STAGES: IndexingStage[] = [
  { id: 'pending', label: 'Queued', order: 1 },
  { id: 'scanning', label: 'Cloning', order: 2 },
  { id: 'parsing', label: 'Parsing', order: 3 },
  { id: 'summarizing', label: 'Summarizing', order: 4 },
  { id: 'indexing', label: 'Embedding', order: 5 },
  { id: 'ready', label: 'Ready', order: 6 },
];

export default function IndexingProgress({ repoId }: { repoId: string }) {
  const router = useRouter();

  const { data: repo, error, refetch, isLoading } = useQuery({
    queryKey: ['repo', repoId],
    queryFn: () => api.getRepo(repoId),
    refetchInterval: 2000, // Poll every 2 seconds
  });

  React.useEffect(() => {
    if (repo?.status === 'ready') {
      router.push(`/repo/${repoId}/overview`);
    }
  }, [repo, repoId, router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-teal-500" />
      </div>
    );
  }

  if (error || repo?.status === 'failed') {
    return (
      <div className="max-w-md mx-auto my-20 p-8 rounded-3xl bg-red-500/10 border border-red-500/20 text-center">
        <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h3 className="text-xl font-bold text-white mb-2">Indexing Failed</h3>
        <p className="text-zinc-400 mb-6">{repo?.status_detail || 'An unexpected error occurred while indexing the repository.'}</p>
        <Button
          onClick={() => refetch()}
          className="bg-red-600 hover:bg-red-500 text-white px-6"
        >
          Retry Analysis
        </Button>
      </div>
    );
  }

  if (!repo) return null;

  const currentStageIndex = STAGES.findIndex(s => s.id === repo.status);
  const progressPercentage = (currentStageIndex / (STAGES.length - 1)) * 100;

  return (
    <div className="max-w-2xl mx-auto my-20 px-6">
      <div className="text-center mb-12">
        <h2 className="text-3xl font-bold text-white mb-3">Analyzing Codebase</h2>
        <p className="text-zinc-400">Greppa is building a semantic map of your project.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-start">
        {/* Stepper */}
        <div className="space-y-6">
          {STAGES.map((stage) => {
            const isCompleted = STAGES.findIndex(s => s.id === repo.status) > stage.order;
            const isCurrent = stage.id === repo.status;

            return (
              <div
                key={stage.id}
                className={`flex items-center gap-4 transition-all duration-500 ${
                  isCurrent ? 'scale-105 opacity-100' : 'opacity-50'
                }`}
              >
                <div className="relative">
                  {isCompleted ? (
                    <CheckCircle2 className="w-6 h-6 text-teal-500" />
                  ) : isCurrent ? (
                    <div className="relative">
                      <Loader2 className="w-6 h-6 animate-spin text-teal-500" />
                    </div>
                  ) : (
                    <Circle className="w-6 h-6 text-zinc-700" />
                  )}
                </div>
                <div className="flex flex-col">
                  <span className={`font-medium ${isCurrent ? 'text-white' : 'text-zinc-500'}`}>
                    {stage.label}
                  </span>
                  {isCurrent && (
                    <span className="text-xs text-zinc-400 animate-pulse">
                      {repo.status_detail}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Stats & Progress */}
        <div className="bg-zinc-900 p-8 rounded-3xl border border-zinc-800 shadow-xl">
          <div className="flex justify-between items-end mb-4">
            <span className="text-sm font-medium text-zinc-400">Total Progress</span>
            <span className="text-2xl font-bold text-teal-500">{Math.round(progressPercentage)}%</span>
          </div>
          <Progress value={progressPercentage} className="h-2 bg-zinc-800" />

          <div className="mt-8 grid grid-cols-2 gap-4">
            <div className="p-4 rounded-2xl bg-zinc-800/50 border border-zinc-700">
              <div className="text-xs text-zinc-500 mb-1">Files Found</div>
              <div className="text-xl font-mono font-bold text-white">{repo.stats.total_files}</div>
            </div>
            <div className="p-4 rounded-2xl bg-zinc-800/50 border border-zinc-700">
              <div className="text-xs text-zinc-500 mb-1">Lines of Code</div>
              <div className="text-xl font-mono font-bold text-white">{repo.stats.total_lines.toLocaleString()}</div>
            </div>
          </div>

          <div className="mt-6 flex items-center justify-between text-xs text-zinc-500">
            <div className="flex items-center gap-2">
              <RefreshCcw className="w-3 h-3 animate-spin" />
              Polling for updates...
            </div>
            <div>
              ID: {repo.id}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
