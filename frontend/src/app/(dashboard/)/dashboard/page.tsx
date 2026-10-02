'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Plus, ExternalLink, Loader2, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { api } from '@/lib/api/client';
import { Repo } from '@/types';
import Link from 'next/link';

export default function DashboardPage() {
  const { data: repos, isLoading, error } = useQuery({
    queryKey: ['repos'],
    queryFn: () => api.listRepos(),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-teal-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen text-red-500">
        Error loading repositories.
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-12">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-12">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">Your Codebases</h1>
          <p className="text-zinc-400">Manage and explore your indexed repositories.</p>
        </div>
        <Button className="bg-teal-600 hover:bg-teal-500 text-white px-6 py-6 rounded-2xl gap-2 text-lg font-semibold transition-all">
          <Plus className="w-5 h-5" />
          Analyze New Repo
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* User Repos */}
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xl font-semibold text-zinc-300 mb-4 flex items-center gap-2">
            <Search className="w-5 h-5" />
            Indexed Repositories
          </h2>

          {repos?.length === 0 ? (
            <div className="p-12 rounded-3xl border-2 border-dashed border-zinc-800 text-center">
              <p className="text-zinc-500 mb-4">No repositories analyzed yet.</p>
              <Button variant="outline" className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
                Get Started
              </Button>
            </div>
          ) : (
            <div className="grid gap-4">
              {repos?.map((repo) => (
                <div
                  key={repo.id}
                  className="group p-6 rounded-2xl bg-zinc-900 border border-zinc-800 hover:border-teal-500/50 transition-all flex items-center justify-between"
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-3 h-3 rounded-full ${
                      repo.status === 'ready' ? 'bg-teal-500' : 'bg-yellow-500 animate-pulse'
                    }`} />
                    <div>
                      <h3 className="font-bold text-white group-hover:text-teal-400 transition-colors">{repo.name}</h3>
                      <div className="flex items-center gap-3 text-xs text-zinc-500 mt-1">
                        <span>{repo.stats.total_files} files</span>
                        <span>•</span>
                        <span>{repo.stats.total_lines.toLocaleString()} lines</span>
                        <span>•</span>
                        <span className="capitalize">{repo.status}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" asChild className="text-zinc-400 hover:text-white">
                      <Link href={`https://github.com/${repo.url_or_path}`} target="_blank">
                        <ExternalLink className="w-4 h-4" />
                      </Link>
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      asChild
                      className={`rounded-xl ${repo.status === 'ready' ? 'bg-zinc-800 hover:bg-zinc-700 text-white' : 'bg-zinc-800 opacity-50 cursor-not-allowed'}`}
                    >
                      <Link href={`/repo/${repo.id}`}>
                        Explore
                      </Link>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Featured Repos */}
        <div className="space-y-6">
          <h2 className="text-xl font-semibold text-zinc-300 mb-4">Featured Repos</h2>
          <div className="space-y-4">
            {[
              { name: 'facebook/react', desc: 'The library for web and native user interfaces.' },
              { name: 'vercel/next.js', desc: 'The React Framework for the Web.' },
              { name: 'tailwindlabs/tailwindcss', desc: 'A utility-first CSS framework.' },
            ].map((featured, i) => (
              <div key={i} className="p-4 rounded-2xl bg-zinc-900 border border-zinc-800 hover:border-zinc-700 transition-all cursor-pointer group">
                <h3 className="font-medium text-zinc-200 group-hover:text-teal-400 transition-colors">{featured.name}</h3>
                <p className="text-xs text-zinc-500 mt-1 line-clamp-2">{featured.desc}</p>
                <Button variant="link" className="p-0 h-auto mt-3 text-xs text-teal-500 hover:text-teal-400">
                  Analyze Now $\rightarrow$
                </Button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
