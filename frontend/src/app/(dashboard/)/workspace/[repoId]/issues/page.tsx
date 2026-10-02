'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import { Search, Filter, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { api } from '@/lib/api/client';
import IssueDetailDrawer from '@/components/features/issues/IssueDetailDrawer';
import { Issue } from '@/types';
import { cn } from '@/lib/utils';

export default function IssuesPage() {
  const params = useParams();
  const repoId = params.repoId as string;
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState('all');

  const { data: issues, isLoading, error } = useQuery({
    queryKey: ['issues', repoId],
    queryFn: () => api.getGoodFirstIssues(repoId),
    enabled: !!repoId,
  });

  const filteredIssues = issues?.filter(issue => {
    const matchesSearch = issue.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         issue.body.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesDifficulty = difficultyFilter === 'all' || issue.difficulty.toLowerCase() === difficultyFilter;
    return matchesSearch && matchesDifficulty;
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-zinc-950">
        <Loader2 className="w-8 h-8 animate-spin text-teal-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-zinc-950 text-red-500">
        Error loading issues.
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-12 space-y-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">First Contributions</h1>
          <p className="text-zinc-400">Find the easiest way to start contributing to this project.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <Input
              placeholder="Search issues..."
              className="pl-9 bg-zinc-900 border-zinc-800 text-zinc-200 w-64"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2 bg-zinc-900 p-1 rounded-lg border border-zinc-800">
            <Filter className="w-4 h-4 text-zinc-500 ml-2" />
            {['all', 'easy', 'medium', 'hard'].map((diff) => (
              <Button
                key={diff}
                variant={difficultyFilter === diff ? 'secondary' : 'ghost'}
                size="sm"
                className={cn(
                  "text-xs capitalize rounded-md h-7 px-3",
                  difficultyFilter === diff ? "bg-teal-600 text-white hover:bg-teal-500" : "text-zinc-400 hover:text-zinc-200"
                )}
                onClick={() => setDifficultyFilter(diff)}
              >
                {diff}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {filteredIssues?.length === 0 ? (
        <div className="p-20 rounded-3xl border-2 border-dashed border-zinc-800 text-center space-y-4">
          <AlertCircle className="w-12 h-12 text-zinc-700 mx-auto" />
          <p className="text-zinc-500 text-lg">No matching issues found.</p>
          <Button
            variant="link"
            className="text-teal-500 hover:text-teal-400"
            onClick={() => { setSearchQuery(''); setDifficultyFilter('all'); }}
          >
            Clear all filters
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredIssues?.map((issue) => (
            <div
              key={issue.number}
              onClick={() => setSelectedIssue(issue)}
              className="p-6 rounded-2xl bg-zinc-900 border border-zinc-800 hover:border-teal-500/50 transition-all cursor-pointer group hover:-translate-y-1"
            >
              <div className="flex justify-between items-start mb-4">
                <span className="text-xs font-mono text-zinc-500">#{issue.number}</span>
                <span className={cn(
                  "text-[10px] font-bold px-2 py-0.5 rounded-full uppercase",
                  issue.difficulty === 'easy' ? 'bg-green-500/10 text-green-500' :
                  issue.difficulty === 'medium' ? 'bg-yellow-500/10 text-yellow-500' :
                  'bg-red-500/10 text-red-500'
                )}>
                  {issue.difficulty}
                </span>
              </div>
              <h3 className="text-lg font-bold text-white mb-3 group-hover:text-teal-400 transition-colors line-clamp-2">
                {issue.title}
              </h3>
              <div className="flex flex-wrap gap-2 mb-6">
                {issue.labels.map(label => (
                  <span key={label} className="text-[10px] px-2 py-0.5 rounded-md bg-zinc-800 text-zinc-400 border border-zinc-700">
                    {label}
                  </span>
                ))}
              </div>
              <div className="flex items-center justify-between mt-auto">
                <div className="text-xs text-zinc-500">
                  {issue.matched_files.length} matched files
                </div>
                <Button size="sm" variant="ghost" className="text-teal-500 hover:text-teal-400 hover:bg-teal-500/10 p-0 h-auto text-xs font-bold">
                  View Plan $\rightarrow$
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedIssue && (
        <IssueDetailDrawer
          issue={selectedIssue}
          onClose={() => setSelectedIssue(null)}
        />
      )}
    </div>
  );
}
