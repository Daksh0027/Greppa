"use client";

import React, { useState } from "react";
import { FolderGit2, RefreshCw, Plus, CheckCircle, AlertCircle, Info, Sparkles, X } from "lucide-react";
import { createRepository, syncRepository } from "@/lib/api";

interface RepoSelectorProps {
  repos: any[];
  currentRepo: any;
  onSelectRepo: (repo: any) => void;
  onRefresh: () => void;
}

export default function RepoSelector({ repos, currentRepo, onSelectRepo, onRefresh }: RepoSelectorProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [urlOrPath, setUrlOrPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !urlOrPath.trim() || loading) return;

    setLoading(true);
    try {
      const newRepo = await createRepository({ name: name.trim(), url_or_path: urlOrPath.trim() });
      setIsModalOpen(false);
      setName("");
      setUrlOrPath("");
      onRefresh();
      onSelectRepo(newRepo);
    } catch (err: any) {
      alert(err.message || "Failed to create repo");
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    if (!currentRepo || syncing) return;
    setSyncing(true);
    try {
      await syncRepository(currentRepo.id);
      onRefresh();
    } catch (err) {
      console.error(err);
    } finally {
      setTimeout(() => setSyncing(false), 1200);
    }
  };

  return (
    <div className="bg-zinc-900 border-b border-zinc-800 px-6 py-3 flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <FolderGit2 className="text-blue-400" size={20} />
          <select
            value={currentRepo?.id || ""}
            onChange={(e) => {
              const r = repos.find((repo) => repo.id === parseInt(e.target.value));
              if (r) onSelectRepo(r);
            }}
            className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm font-semibold text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {repos.length === 0 && <option value="">No repositories indexed</option>}
            {repos.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name} ({r.status})
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 px-3 py-1.5 rounded-lg text-xs font-medium transition"
        >
          <Plus size={14} /> Add Repository
        </button>

        {repos.length === 0 && (
          <button
            onClick={async () => {
              const demo = await import("@/lib/api").then((m) => m.createDemoRepository());
              onRefresh();
              onSelectRepo(demo);
            }}
            className="flex items-center gap-1.5 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 px-3 py-1.5 rounded-lg text-xs font-medium transition"
          >
            <Sparkles size={13} /> Load Demo Repo
          </button>
        )}

        {currentRepo && (
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 px-3 py-1.5 rounded-lg text-xs font-medium transition"
            title="Incremental sync: re-process only changed files & dependents"
          >
            <RefreshCw size={13} className={syncing ? "animate-spin text-blue-400" : ""} />
            Incremental Sync
          </button>
        )}
      </div>

      {currentRepo && (
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                currentRepo.status === "ready"
                  ? "bg-emerald-500"
                  : currentRepo.status === "failed"
                  ? "bg-red-500"
                  : "bg-amber-500 animate-pulse"
              }`}
            />
            <span className="capitalize font-medium text-zinc-300">
              {currentRepo.status} {currentRepo.status_detail ? `• ${currentRepo.status_detail}` : ""}
            </span>
          </div>

          {currentRepo.stats && currentRepo.stats.total_files && (
            <div className="hidden md:flex items-center gap-3 text-zinc-400 font-mono text-[11px] bg-zinc-950 px-3 py-1 rounded-md border border-zinc-800">
              <span>{currentRepo.stats.total_files} files</span>
              <span>•</span>
              <span>{currentRepo.stats.total_symbols} AST symbols</span>
              <span>•</span>
              <span>{currentRepo.stats.total_lines} lines</span>
            </div>
          )}
        </div>
      )}

      {/* New Repo Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-zinc-900 border border-zinc-700 w-full max-w-md rounded-xl p-6 shadow-2xl relative text-zinc-100">
            <button onClick={() => setIsModalOpen(false)} className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-200">
              <X size={18} />
            </button>

            <h3 className="text-base font-bold mb-1">Index New Repository</h3>
            <p className="text-xs text-zinc-400 mb-4">
              Enter a local folder path or Git URL to shallow clone and extract AST symbol graph.
            </p>

            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-zinc-400 mb-1">Repository Name</label>
                <input
                  type="text"
                  placeholder="e.g. Greppa or my-project"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-400 mb-1">Path or Git URL</label>
                <input
                  type="text"
                  placeholder="c:\Users\... or https://github.com/org/repo"
                  value={urlOrPath}
                  onChange={(e) => setUrlOrPath(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-zinc-400 hover:bg-zinc-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 rounded-lg text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white flex items-center gap-1.5"
                >
                  {loading ? <RefreshCw size={13} className="animate-spin" /> : null}
                  {loading ? "Starting Ingestion..." : "Start Ingestion"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
