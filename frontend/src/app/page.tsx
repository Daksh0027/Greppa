"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Compass,
  Search,
  GitBranch,
  Bot,
  Settings as SettingsIcon,
  Layers,
  FileText,
  Code2,
  ExternalLink,
  ChevronRight,
  Shield,
  Activity,
  CheckCircle2,
  BookOpen,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import RepoSelector from "@/components/RepoSelector";
import SearchBar from "@/components/SearchBar";
import CodeViewer from "@/components/CodeViewer";
import GraphView from "@/components/GraphView";
import AgentChat from "@/components/AgentChat";
import IssueMatcher from "@/components/IssueMatcher";
import SettingsModal from "@/components/SettingsModal";
import {
  listRepositories,
  getRepository,
  listRepoFiles,
  getFileCode,
  getRepositoryGraph,
  getGuidedTour,
} from "@/lib/api";

export default function GreppaDashboard() {
  const [repos, setRepos] = useState<any[]>([]);
  const [currentRepo, setCurrentRepo] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"tour" | "search" | "graph" | "agent" | "issues">("tour");
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // File & Code Viewer state
  const [files, setFiles] = useState<any[]>([]);
  const [currentFilePath, setCurrentFilePath] = useState("");
  const [currentCode, setCurrentCode] = useState("");
  const [currentLanguage, setCurrentLanguage] = useState("plaintext");
  const [currentSymbols, setCurrentSymbols] = useState<any[]>([]);
  const [highlightRange, setHighlightRange] = useState<{ startLine: number; endLine: number } | null>(null);

  // Graph state
  const [graphData, setGraphData] = useState<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] });

  // Guided Tour state
  const [tourData, setTourData] = useState<any>(null);

  const loadRepos = useCallback(async () => {
    try {
      const data = await listRepositories();
      setRepos(data);
      if (data.length > 0 && !currentRepo) {
        setCurrentRepo(data[0]);
      }
    } catch (err) {
      console.error("Failed to load repos:", err);
    }
  }, [currentRepo]);

  useEffect(() => {
    loadRepos();
  }, [loadRepos]);

  // Load repo specific data when repo changes
  useEffect(() => {
    if (!currentRepo?.id) return;

    listRepoFiles(currentRepo.id)
      .then((fileList) => {
        setFiles(fileList);
        if (fileList.length > 0 && !currentFilePath) {
          openFile(fileList[0].path);
        }
      })
      .catch(console.error);

    getRepositoryGraph(currentRepo.id)
      .then(setGraphData)
      .catch(console.error);

    getGuidedTour(currentRepo.id)
      .then(setTourData)
      .catch(console.error);
  }, [currentRepo?.id]);

  const openFile = async (path: string, startLine?: number, endLine?: number) => {
    if (!currentRepo?.id) return;
    try {
      const fileData = await getFileCode(currentRepo.id, path);
      setCurrentFilePath(fileData.path);
      setCurrentCode(fileData.content);
      setCurrentLanguage(fileData.language);
      setCurrentSymbols(fileData.symbols || []);
      if (startLine) {
        setHighlightRange({ startLine, endLine: endLine || startLine });
      } else {
        setHighlightRange(null);
      }
    } catch (err) {
      console.error("Error opening file:", err);
    }
  };

  const handleOpenCitation = (filePath: string, startLine: number, endLine: number) => {
    setActiveTab("search");
    openFile(filePath, startLine, endLine);
  };

  const handleSelectSymbol = (sym: any) => {
    if (sym.file_path && sym.file_path !== currentFilePath) {
      openFile(sym.file_path, sym.start_line, sym.end_line);
    } else {
      setHighlightRange({ startLine: sym.start_line, endLine: sym.end_line });
    }
  };

  return (
    <div className="flex flex-col h-screen bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* Top Navbar */}
      <header className="h-14 border-b border-zinc-800 bg-zinc-900/90 backdrop-blur px-6 flex items-center justify-between z-30">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center font-bold text-white shadow-md shadow-blue-500/20">
            G
          </div>
          <div>
            <h1 className="font-bold text-sm tracking-tight text-white flex items-center gap-2">
              GREPPA
              <span className="text-[10px] font-mono uppercase bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded border border-blue-500/30">
                Code Intelligence
              </span>
            </h1>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 bg-zinc-950 p-1 rounded-lg border border-zinc-800 text-xs">
          <button
            onClick={() => setActiveTab("tour")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition ${
              activeTab === "tour" ? "bg-zinc-800 text-white shadow-sm" : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Compass size={14} /> Guided Tour
          </button>
          <button
            onClick={() => setActiveTab("search")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition ${
              activeTab === "search" ? "bg-zinc-800 text-white shadow-sm" : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Search size={14} /> Hybrid Search & Code
          </button>
          <button
            onClick={() => setActiveTab("graph")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition ${
              activeTab === "graph" ? "bg-zinc-800 text-white shadow-sm" : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <GitBranch size={14} /> Architecture Graph
          </button>
          <button
            onClick={() => setActiveTab("agent")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition ${
              activeTab === "agent" ? "bg-purple-900/40 text-purple-300 border border-purple-700/50 shadow-sm" : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Bot size={14} /> Agent Reasoning
          </button>
          <button
            onClick={() => setActiveTab("issues")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition ${
              activeTab === "issues" ? "bg-emerald-900/40 text-emerald-300 border border-emerald-700/50 shadow-sm" : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <CheckCircle2 size={14} /> Good-First-Issue
          </button>
        </div>

        {/* Right Settings */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsSettingsOpen(true)}
            className="p-2 rounded-lg bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 transition"
            title="Configure Gemini API Key"
          >
            <SettingsIcon size={16} />
          </button>
        </div>
      </header>

      {/* Subheader: Repo Switcher and Stats */}
      <RepoSelector
        repos={repos}
        currentRepo={currentRepo}
        onSelectRepo={(r) => {
          setCurrentRepo(r);
          setCurrentFilePath("");
          setHighlightRange(null);
        }}
        onRefresh={loadRepos}
      />

      {/* Main Workspace Body */}
      <main className="flex-1 overflow-hidden p-4">
        {activeTab === "tour" && (
          <div className="h-full overflow-y-auto max-w-5xl mx-auto space-y-6 p-4">
            {/* Repo Summary Header */}
            <div className="p-6 bg-zinc-900/90 border border-zinc-800 rounded-xl space-y-3">
              <div className="flex items-center gap-2 text-blue-400 text-xs font-semibold uppercase tracking-wider">
                <Compass size={16} /> Hierarchical Repository Tour
              </div>
              <h2 className="text-xl font-bold text-white">{currentRepo?.name || "Repository"} Overview</h2>
              <div className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">
                {currentRepo?.repo_summary || "Synthesizing whole-repository overview from bottom-up folder and file summaries..."}
              </div>
            </div>

            {/* Auto-Generated Guided Reading Order */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
                  <Activity size={16} className="text-amber-400" />
                  Auto-Generated Reading Order (Ranked by PageRank Importance)
                </h3>
                <span className="text-xs text-zinc-500 font-mono">
                  {tourData?.tour_stops?.length || 0} Recommended Stops
                </span>
              </div>

              <div className="space-y-3">
                {tourData?.tour_stops?.map((stop: any) => (
                  <div
                    key={stop.step}
                    className="p-4 bg-zinc-900/70 border border-zinc-800 hover:border-blue-500/50 rounded-xl transition space-y-2.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="w-6 h-6 rounded-full bg-blue-600/30 text-blue-400 border border-blue-500/40 flex items-center justify-center text-xs font-bold font-mono">
                          {stop.step}
                        </span>
                        <div>
                          <span className="font-mono font-bold text-blue-300 text-sm hover:underline cursor-pointer" onClick={() => {
                            setActiveTab("search");
                            openFile(stop.file_path);
                          }}>
                            {stop.file_path}
                          </span>
                          <span className="text-xs text-zinc-400 ml-2 font-sans">• {stop.tier}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 text-xs">
                        <span className="font-mono text-amber-300 font-semibold" title="PageRank Score">
                          ★ {stop.importance_score}
                        </span>
                        <button
                          onClick={() => {
                            setActiveTab("search");
                            openFile(stop.file_path);
                          }}
                          className="px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded text-xs font-medium flex items-center gap-1 transition"
                        >
                          View Code <ArrowRight size={12} />
                        </button>
                      </div>
                    </div>

                    <p className="text-xs text-zinc-300 leading-relaxed">
                      <strong className="text-zinc-200">Why read this: </strong>
                      {stop.why_read}
                    </p>

                    {/* Key Symbols in File */}
                    {stop.key_symbols && stop.key_symbols.length > 0 && (
                      <div className="pt-2 border-t border-zinc-800/60 flex flex-wrap gap-2 text-xs">
                        <span className="text-zinc-500 text-[11px] flex items-center gap-1">Focus Symbols:</span>
                        {stop.key_symbols.map((sym: any, idx: number) => (
                          <button
                            key={idx}
                            onClick={() => {
                              setActiveTab("search");
                              openFile(stop.file_path, sym.start_line, sym.end_line);
                            }}
                            className="bg-zinc-950 hover:bg-zinc-800 border border-zinc-800 text-blue-300 px-2 py-0.5 rounded text-[11px] font-mono transition"
                          >
                            {sym.name} (L{sym.start_line})
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === "search" && (
          <div className="h-full grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Left Search Pane */}
            <div className="lg:col-span-5 h-full">
              {currentRepo?.id ? (
                <SearchBar
                  repoId={currentRepo.id}
                  onSelectHit={(hit) => {
                    openFile(hit.file_path, hit.start_line, hit.end_line);
                  }}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-zinc-500 text-xs">
                  Please select or add a repository
                </div>
              )}
            </div>

            {/* Right Monaco Code View Pane */}
            <div className="lg:col-span-7 h-full">
              <CodeViewer
                code={currentCode}
                filePath={currentFilePath}
                language={currentLanguage}
                highlightRange={highlightRange}
                symbols={currentSymbols}
                onSelectSymbol={handleSelectSymbol}
              />
            </div>
          </div>
        )}

        {activeTab === "graph" && (
          <div className="h-full">
            <GraphView
              nodes={graphData.nodes}
              edges={graphData.edges}
              onSelectSymbol={(symData) => {
                setActiveTab("search");
                openFile(symData.file_path, symData.start_line, symData.end_line);
              }}
            />
          </div>
        )}

        {activeTab === "agent" && (
          <div className="h-full grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-7 h-full">
              {currentRepo?.id ? (
                <AgentChat
                  repoId={currentRepo.id}
                  onOpenCitation={handleOpenCitation}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-zinc-500 text-xs">
                  Please select or add a repository
                </div>
              )}
            </div>
            <div className="lg:col-span-5 h-full">
              <CodeViewer
                code={currentCode}
                filePath={currentFilePath}
                language={currentLanguage}
                highlightRange={highlightRange}
                symbols={currentSymbols}
                onSelectSymbol={handleSelectSymbol}
              />
            </div>
          </div>
        )}

        {activeTab === "issues" && (
          <div className="h-full grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-7 h-full">
              {currentRepo?.id ? (
                <IssueMatcher
                  repoId={currentRepo.id}
                  onOpenFile={(fPath, sLine, eLine) => {
                    openFile(fPath, sLine, eLine);
                  }}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-zinc-500 text-xs">
                  Please select or add a repository
                </div>
              )}
            </div>
            <div className="lg:col-span-5 h-full">
              <CodeViewer
                code={currentCode}
                filePath={currentFilePath}
                language={currentLanguage}
                highlightRange={highlightRange}
                symbols={currentSymbols}
                onSelectSymbol={handleSelectSymbol}
              />
            </div>
          </div>
        )}
      </main>

      {/* Settings Modal */}
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </div>
  );
}
