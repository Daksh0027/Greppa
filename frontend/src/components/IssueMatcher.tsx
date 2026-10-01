"use client";

import React, { useState } from "react";
import { CheckCircle2, AlertTriangle, ArrowRight, BookOpen, Layers, Loader2, Sparkles } from "lucide-react";
import { matchGoodFirstIssue } from "@/lib/api";

interface IssueMatcherProps {
  repoId: number;
  onOpenFile: (filePath: string, startLine?: number, endLine?: number) => void;
}

const PRESET_ISSUES = [
  {
    title: "Add token expiry check to authentication flow",
    description: "Expired authentication tokens should be rejected with a 401 Unauthorized status instead of attempting to verify hash.",
  },
  {
    title: "Implement rate limiting middleware on login endpoint",
    description: "Prevent brute-force password guessing by limiting login requests to 5 attempts per minute per IP address.",
  },
  {
    title: "Add cache invalidation for modified AST symbol files",
    description: "Ensure that when a file is modified, its cached bottom-up summaries are evicted and re-computed.",
  },
];

export default function IssueMatcher({ repoId, onOpenFile }: IssueMatcherProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleMatch = async (t: string, d: string) => {
    if (!t.trim() || loading) return;
    setLoading(true);
    setResult(null);
    try {
      const data = await matchGoodFirstIssue(repoId, t.trim(), d.trim());
      setResult(data);
    } catch (err: any) {
      alert(err.message || "Failed to analyze issue");
    } finally {
      setLoading(false);
    }
  };

  const getDifficultyBadge = (difficulty: string, color: string) => {
    switch (color) {
      case "emerald":
        return <span className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2.5 py-1 rounded text-xs font-semibold">{difficulty}</span>;
      case "amber":
        return <span className="bg-amber-500/20 text-amber-400 border border-amber-500/30 px-2.5 py-1 rounded text-xs font-semibold">{difficulty}</span>;
      default:
        return <span className="bg-red-500/20 text-red-400 border border-red-500/30 px-2.5 py-1 rounded text-xs font-semibold">{difficulty}</span>;
    }
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden shadow-lg">
      <div className="p-4 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-emerald-600/20 text-emerald-400 rounded-lg">
            <CheckCircle2 size={18} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-100">Good-First-Issue & Contributor Onboarding</h3>
            <p className="text-xs text-zinc-400">Match bug reports or feature requests to exact code locations & implementation roadmaps</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* Preset Issues */}
        <div>
          <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider block mb-2">
            Try a Preset Issue or Describe Your Own:
          </span>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            {PRESET_ISSUES.map((p, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setTitle(p.title);
                  setDescription(p.description);
                  handleMatch(p.title, p.description);
                }}
                className="text-left p-2.5 bg-zinc-900 hover:bg-zinc-800/80 border border-zinc-800 rounded-lg transition text-xs space-y-1"
              >
                <div className="font-semibold text-blue-300 truncate">{p.title}</div>
                <div className="text-[11px] text-zinc-400 line-clamp-2">{p.description}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Custom Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleMatch(title, description);
          }}
          className="bg-zinc-900/60 p-4 border border-zinc-800 rounded-xl space-y-3"
        >
          <div>
            <label className="block text-xs font-semibold text-zinc-400 mb-1">Issue Title</label>
            <input
              type="text"
              placeholder="e.g. Fix null pointer in token validation"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-zinc-400 mb-1">Issue Description / Expected Behavior</label>
            <textarea
              rows={2}
              placeholder="Describe the bug or feature requirement..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading || !title.trim()}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition disabled:opacity-50"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
              {loading ? "Analyzing Code Graph..." : "Analyze Issue & Match Code"}
            </button>
          </div>
        </form>

        {loading && (
          <div className="p-8 text-center flex flex-col items-center justify-center gap-2 text-zinc-400 text-xs">
            <Loader2 size={24} className="animate-spin text-emerald-400" />
            <span>Searching symbols, tracing fan-out & building implementation guide...</span>
          </div>
        )}

        {result && (
          <div className="space-y-4 animate-in fade-in duration-300">
            {/* Header Result */}
            <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-xl flex items-center justify-between">
              <div>
                <span className="text-xs text-zinc-400">Calculated Complexity:</span>
                <div className="mt-1">{getDifficultyBadge(result.difficulty, result.difficulty_color)}</div>
              </div>
              <div className="text-right text-xs text-zinc-400">
                <span>Affected Subgraph:</span>
                <div className="font-mono font-bold text-zinc-200 mt-1">{result.affected_files.length} files impacted</div>
              </div>
            </div>

            {/* Impacted Primary Symbols */}
            {result.primary_symbols && result.primary_symbols.length > 0 && (
              <div className="p-4 bg-zinc-900/80 border border-zinc-800 rounded-xl space-y-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
                  <Layers size={13} className="text-blue-400" /> Primary Code Locations to Inspect:
                </span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
                  {result.primary_symbols.map((sym: any, idx: number) => (
                    <div
                      key={idx}
                      onClick={() => onOpenFile(sym.file_path, sym.start_line, sym.end_line)}
                      className="p-2.5 bg-zinc-950 border border-zinc-800 hover:border-emerald-500/50 rounded-lg cursor-pointer transition flex items-center justify-between text-xs"
                    >
                      <div className="truncate">
                        <span className="font-mono font-bold text-blue-300 block truncate">{sym.symbol_name}</span>
                        <span className="text-[11px] text-zinc-500 font-mono">{sym.file_path}:{sym.start_line}</span>
                      </div>
                      <span className="text-[10px] font-mono bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded">
                        ★ {sym.importance_score}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actionable Implementation Roadmap */}
            <div className="p-4 bg-zinc-900/90 border border-zinc-800 rounded-xl space-y-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                <BookOpen size={14} /> Contributor Implementation Roadmap
              </span>
              <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap font-sans pt-1">
                {result.roadmap}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
