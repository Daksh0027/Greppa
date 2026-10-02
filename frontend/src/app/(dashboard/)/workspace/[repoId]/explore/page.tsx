'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, useRouter } from 'next/navigation';
import Editor from '@monaco-editor/react';
import {
  FileText,
  Search,
  Maximize2,
  ChevronRight,
  Info,
  Zap,
  Layers
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api/client';
import FileExplorer from '@/components/features/explorer/FileExplorer';
import { cn } from '@/lib/utils';

export default function ExplorePage() {
  const params = useParams();
  const router = useRouter();
  const repoId = params.repoId as string;

  const [activeFile, setActiveFile] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortByImportance, setSortByImportance] = useState(false);
  const [isSymbolPanelOpen, setIsSymbolPanelOpen] = useState(true);

  const { data: fileData, isLoading: isFileLoading } = useQuery({
    queryKey: ['file', repoId, activeFile],
    queryFn: () => api.getFileContent(repoId, activeFile),
    enabled: !!activeFile,
  });

  const { data: repoFiles, isLoading: isFilesLoading } = useQuery({
    queryKey: ['files', repoId],
    queryFn: () => api.listRepoFiles(repoId),
    enabled: !!repoId,
  });

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-zinc-950">
      {/* Left: File Explorer */}
      <div className="w-72 flex-shrink-0">
        <FileExplorer
          nodes={repoFiles || []}
          selectedPath={activeFile}
          onSelect={setActiveFile}
          searchQuery={searchQuery}
          sortByImportance={sortByImportance}
        />
      </div>

      {/* Center: Code Viewer */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* File Tab/Header */}
        <div className="h-12 border-b border-zinc-800 flex items-center justify-between px-4 bg-zinc-900/50">
          <div className="flex items-center gap-2 text-sm text-zinc-400 truncate">
            <FileText className="w-4 h-4 text-teal-500" />
            <span className="font-mono">{activeFile || 'Select a file to explore'}</span>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => setIsSymbolPanelOpen(!isSymbolPanelOpen)} className="h-8 w-8 p-0">
              <Layers className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
              <Maximize2 className="w-4 h-4" />
            </Button>
          </div>
        </div>

        <div className="flex-1 relative">
          {activeFile ? (
            isFileLoading ? (
              <div className="absolute inset-0 flex items-center justify-center bg-zinc-950/50 backdrop-blur-sm z-10">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-teal-500" />
              </div>
            ) : (
              <Editor
                height="100%"
                theme="vs-dark"
                path={activeFile}
                defaultLanguage={fileData?.language || 'typescript'}
                value={fileData?.content || ''}
                options={{
                  fontSize: 14,
                  fontFamily: 'JetBrains Mono, monospace',
                  minimap: { enabled: true },
                  scrollBeyondLastLine: false,
                  readOnly: true,
                  padding: { top: 16 },
                }}
              />
            )
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-zinc-600 p-12 text-center">
              <div className="w-20 h-20 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-6">
                <Search className="w-10 h-10 opacity-20" />
              </div>
              <h3 className="text-xl font-medium text-zinc-400 mb-2">No file selected</h3>
              <p className="max-w-xs text-sm opacity-60">Select a file from the sidebar or use Cmd+K to search for symbols.</p>
            </div>
          )}
        </div>
      </div>

      {/* Right: Symbol Outline & AI Summary */}
      {isSymbolPanelOpen && (
        <div className="w-80 flex-shrink-0 border-l border-zinc-800 bg-zinc-900/30 flex flex-col">
          {activeFile ? (
            <div className="flex flex-col h-full">
              {/* AI Summary */}
              <div className="p-4 border-b border-zinc-800">
                <div className="flex items-center gap-2 text-teal-500 text-xs font-bold uppercase tracking-wider mb-3">
                  <Zap className="w-3 h-3" />
                  AI Summary
                </div>
                <p className="text-sm text-zinc-300 leading-relaxed">
                  This file manages the core routing logic for the API. It coordinates between the authentication middleware and the repository controllers.
                </p>
              </div>

              {/* Symbol Outline */}
              <div className="flex-1 overflow-y-auto p-4">
                <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-4">Symbols</h4>
                <div className="space-y-1">
                  {fileData?.symbols?.map((sym, i) => (
                    <button
                      key={i}
                      className="w-full text-left px-2 py-1.5 rounded hover:bg-zinc-800 text-sm text-zinc-400 hover:text-teal-400 transition-colors flex items-center gap-2 group"
                    >
                      <ChevronRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                      <span className="truncate">{sym.name}</span>
                      <span className="text-[10px] opacity-40 ml-auto">{sym.start_line}</span>
                    </button>
                  ))}
                  {(!fileData?.symbols || fileData.symbols.length === 0) && (
                    <p className="text-xs text-zinc-600 italic">No symbols detected.</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center p-8 text-center">
              <div className="text-zinc-600 text-sm">
                <Info className="w-8 h-8 mx-auto mb-3 opacity-20" />
                Select a file to see its structure and AI analysis.
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
