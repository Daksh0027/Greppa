"use client";

import React, { useState } from "react";
import { Sparkles, ArrowRight, CheckCircle2, ChevronDown, ChevronRight, Terminal, BookOpen, Loader2 } from "lucide-react";
import { runAgentQuery } from "@/lib/api";

interface AgentChatProps {
  repoId: number;
  onOpenCitation: (filePath: string, startLine: number, endLine: number) => void;
}

export default function AgentChat({ repoId, onOpenCitation }: AgentChatProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({});

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    setLoading(true);
    setResult(null);
    try {
      const res = await runAgentQuery(repoId, query.trim());
      setResult(res);
      // Auto expand first step
      setExpandedSteps({ 1: true });
    } catch (err: any) {
      alert(err.message || "Agent execution failed");
    } finally {
      setLoading(false);
    }
  };

  const toggleStep = (stepNum: number) => {
    setExpandedSteps((prev) => ({ ...prev, [stepNum]: !prev[stepNum] }));
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden shadow-lg">
      <div className="p-4 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-purple-600/20 text-purple-400 rounded-lg">
            <Sparkles size={18} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-100">Deep Architecture Reasoning Agent</h3>
            <p className="text-xs text-zinc-400">Iterative search, call hierarchy tracing & citation-backed answers</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <form onSubmit={handleAsk} className="flex gap-2">
          <input
            type="text"
            placeholder="e.g. How does user authentication work end-to-end?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />}
            {loading ? "Reasoning..." : "Ask Agent"}
          </button>
        </form>

        {loading && (
          <div className="p-6 bg-zinc-900/50 rounded-xl border border-zinc-800 flex flex-col items-center justify-center gap-3 text-center">
            <Loader2 size={28} className="animate-spin text-purple-400" />
            <div>
              <p className="text-sm font-medium text-zinc-200">Executing Multi-Step Agent Loop</p>
              <p className="text-xs text-zinc-400 mt-0.5">Searching symbols, resolving call edges, and packing context under token budget...</p>
            </div>
          </div>
        )}

        {result && (
          <div className="space-y-4 animate-in fade-in duration-300">
            {/* Reasoning Steps */}
            {result.steps && result.steps.length > 0 && (
              <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-3 space-y-2">
                <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Terminal size={14} className="text-purple-400" />
                  Agent Reasoning Trajectory ({result.steps.length} Steps)
                </span>

                <div className="space-y-2 pt-1">
                  {result.steps.map((step: any) => {
                    const isExpanded = expandedSteps[step.step_number];
                    return (
                      <div key={step.step_number} className="border border-zinc-800 bg-zinc-900 rounded-lg overflow-hidden text-xs">
                        <button
                          onClick={() => toggleStep(step.step_number)}
                          className="w-full px-3 py-2 flex items-center justify-between text-left hover:bg-zinc-800/60 transition"
                        >
                          <div className="flex items-center gap-2">
                            <span className="w-5 h-5 rounded-full bg-purple-900/60 text-purple-300 flex items-center justify-center text-[10px] font-mono">
                              {step.step_number}
                            </span>
                            <span className="font-medium text-zinc-200 truncate max-w-[500px]">
                              {step.action}: {step.thought}
                            </span>
                          </div>
                          {isExpanded ? <ChevronDown size={14} className="text-zinc-400" /> : <ChevronRight size={14} className="text-zinc-400" />}
                        </button>

                        {isExpanded && (
                          <div className="p-3 bg-zinc-950/70 border-t border-zinc-800/80 space-y-2 font-mono text-[11px]">
                            <div>
                              <span className="text-purple-400 font-semibold">Action Input: </span>
                              <span className="text-zinc-300">{JSON.stringify(step.action_input)}</span>
                            </div>
                            <div>
                              <span className="text-blue-400 font-semibold">Observation: </span>
                              <pre className="text-zinc-400 mt-1 whitespace-pre-wrap font-sans text-xs bg-zinc-900 p-2 rounded">
                                {step.observation}
                              </pre>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Final Answer */}
            <div className="bg-zinc-900/90 border border-zinc-800 rounded-xl p-4 shadow">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-2 flex items-center gap-1.5">
                <CheckCircle2 size={14} /> Synthesized Architecture Answer
              </h4>
              <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap font-sans">
                {result.answer}
              </div>

              {/* Citations */}
              {result.citations && result.citations.length > 0 && (
                <div className="mt-4 pt-3 border-t border-zinc-800">
                  <span className="text-xs font-semibold text-zinc-400 flex items-center gap-1.5 mb-2">
                    <BookOpen size={13} className="text-blue-400" /> Clickable Code Citations:
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {result.citations.map((c: any, idx: number) => (
                      <button
                        key={idx}
                        onClick={() => onOpenCitation(c.file_path, c.start_line, c.end_line)}
                        className="bg-zinc-800 hover:bg-zinc-700 text-blue-300 hover:text-blue-200 border border-zinc-700 px-2.5 py-1 rounded text-xs font-mono flex items-center gap-1 transition"
                      >
                        <span>{c.file_path}</span>
                        <span className="text-zinc-500">:{c.start_line}-{c.end_line}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
