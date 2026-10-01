"use client";

import React, { useState } from "react";
import { Search, GitPullRequest, ArrowUpRight, ArrowDownLeft, Layers, Loader2 } from "lucide-react";
import { hybridSearch } from "@/lib/api";

interface SearchBarProps {
  repoId: number;
  onSelectHit: (hit: any) => void;
}

export default function SearchBar({ repoId, onSelectHit }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [expandedContexts, setExpandedContexts] = useState<any[]>([]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    setLoading(true);
    try {
      const data = await hybridSearch(repoId, query.trim(), 12);
      setResults(data.hits || []);
      setExpandedContexts(data.expanded_graph_contexts || []);
    } catch (err) {
      console.error("Search error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden shadow-lg">
      <div className="p-3 bg-zinc-900 border-b border-zinc-800">
        <form onSubmit={handleSearch} className="relative">
          <input
            type="text"
            placeholder="Search symbols, functions, classes (hybrid vector + keyword)..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-zinc-950 border border-zinc-700 rounded-lg pl-9 pr-20 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <Search size={16} className="absolute left-3 top-3 text-zinc-400" />
          <button
            type="submit"
            disabled={loading}
            className="absolute right-1.5 top-1.5 px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-medium transition"
          >
            {loading ? <Loader2 size={13} className="animate-spin" /> : "Search"}
          </button>
        </form>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {results.length === 0 && !loading && (
          <div className="text-center py-10 text-zinc-500 text-xs">
            Enter a query to run hybrid search (e.g. "authenticate user", "parse tokens", "handle_request")
          </div>
        )}

        {results.map((hit, idx) => {
          const graphCtx = expandedContexts.find((c) => c.symbol.chunk_id === hit.chunk_id);

          return (
            <div
              key={hit.chunk_id || idx}
              onClick={() => onSelectHit(hit)}
              className="p-3 bg-zinc-900/70 hover:bg-zinc-900 border border-zinc-800/80 hover:border-blue-500/50 rounded-lg cursor-pointer transition space-y-1.5"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-sm text-blue-300">
                    {hit.symbol_name || hit.file_path}
                  </span>
                  <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 bg-zinc-800 text-zinc-400 rounded">
                    Line {hit.start_line}-{hit.end_line}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-mono text-amber-300 text-[11px]" title="PageRank Architectural Centrality">
                    ★ {hit.importance_score}
                  </span>
                  <span className="font-mono text-zinc-400 text-[11px] bg-zinc-800 px-1.5 py-0.5 rounded">
                    RRF {hit.score}
                  </span>
                </div>
              </div>

              <div className="text-xs text-zinc-400 font-mono truncate">
                {hit.file_path} {hit.header ? `• ${hit.header}` : ""}
              </div>

              {hit.summary && (
                <div className="text-xs text-zinc-300 line-clamp-2">
                  {hit.summary}
                </div>
              )}

              {/* Expanded Call Graph Meta */}
              {graphCtx && (graphCtx.callers.length > 0 || graphCtx.callees.length > 0) && (
                <div className="pt-2 border-t border-zinc-800/60 flex flex-wrap gap-x-4 gap-y-1 text-[11px]">
                  {graphCtx.callers.length > 0 && (
                    <div className="flex items-center gap-1 text-emerald-400">
                      <ArrowDownLeft size={12} />
                      <span>Called by: {graphCtx.callers.map((c: any) => c.symbol_name).slice(0, 2).join(", ")}</span>
                    </div>
                  )}
                  {graphCtx.callees.length > 0 && (
                    <div className="flex items-center gap-1 text-blue-400">
                      <ArrowUpRight size={12} />
                      <span>Calls: {graphCtx.callees.map((c: any) => c.symbol_name).slice(0, 2).join(", ")}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
