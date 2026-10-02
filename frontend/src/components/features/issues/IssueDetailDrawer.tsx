'use client';

import React from 'react';
import { CheckCircle2, Circle, FileCode, ExternalLink, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface IssueStep {
  order: number;
  title: string;
  description: string;
}

interface IssueDetailProps {
  issue: any; // Will be typed once the Issue type is fully refined
  onClose: () => void;
}

export default function IssueDetailDrawer({ issue, onClose }: IssueDetailProps) {
  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-zinc-900 border-l border-zinc-800 shadow-2xl flex flex-col animate-in slide-in-from-right duration-300 z-50">
      <div className="p-6 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-zinc-500 font-mono text-sm">#{issue.number}</span>
          <h2 className="text-xl font-bold text-white">{issue.title}</h2>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose} className="text-zinc-400 hover:text-white">
          Close
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-8">
        {/* Summary */}
        <section>
          <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-3">Overview</h3>
          <p className="text-zinc-300 leading-relaxed">{issue.body}</p>
        </section>

        {/* Likely Files */}
        <section>
          <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-3">Likely Files</h3>
          <div className="grid gap-3">
            {issue.matched_files.map((file: any, i: number) => (
              <div key={i} className="p-3 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-between group hover:border-teal-500/50 transition-all">
                <div className="flex items-center gap-3 overflow-hidden">
                  <FileCode className="w-4 h-4 text-teal-500 flex-shrink-0" />
                  <span className="text-sm text-zinc-300 truncate font-mono">{file.file_path}</span>
                </div>
                <div className="flex items-center gap-3 ml-4">
                  <span className="text-xs text-zinc-500 font-mono">{Math.round(file.relevance_score * 100)}% match</span>
                  <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-teal-500 hover:text-teal-400 hover:bg-teal-500/10">
                    Explore
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Contribution Plan */}
        <section>
          <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-3">Suggested Plan</h3>
          <div className="p-4 rounded-2xl bg-zinc-950 border border-zinc-800 text-zinc-300 text-sm leading-relaxed whitespace-pre-wrap">
            {issue.contribution_plan}
          </div>
        </section>

        {/* PR Checklist */}
        <section className="p-6 rounded-3xl bg-zinc-800/30 border border-zinc-700/50">
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-teal-500" />
            Before you open a PR
          </h3>
          <div className="space-y-3">
            {[
              'Verify the fix with existing tests',
              'Run the linting check: npm run lint',
              'Ensure no new console.logs are added',
              'Update relevant documentation if needed'
            ].map((item, i) => (
              <label key={i} className="flex items-center gap-3 cursor-pointer group">
                <div className="relative flex items-center justify-center">
                  <input type="checkbox" className="peer appearance-none w-4 h-4 border border-zinc-600 rounded bg-zinc-900 checked:bg-teal-500 checked:border-teal-500 transition-all" />
                  <CheckCircle2 className="absolute w-3 h-3 text-white opacity-0 peer-checked:opacity-100 pointer-events-none" />
                </div>
                <span className="text-sm text-zinc-400 group-hover:text-zinc-200 transition-colors">{item}</span>
              </label>
            ))}
          </div>
        </section>
      </div>

      <div className="p-6 border-t border-zinc-800 bg-zinc-900/50 flex justify-end">
        <Button className="bg-teal-600 hover:bg-teal-500 text-white px-6 rounded-xl font-bold">
          Open Issue on GitHub <ExternalLink className="ml-2 w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}
