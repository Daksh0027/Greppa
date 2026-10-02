'use client';

import React, { useState, useMemo } from 'react';
import {
  Folder,
  File,
  ChevronRight,
  ChevronDown,
  Search,
  FileCode,
  MoreVertical,
  Zap
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface FileNode {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
  importance?: number;
}

interface FileTreeProps {
  nodes: FileNode[];
  selectedPath: string;
  onSelect: (path: string) => void;
  searchQuery: string;
  sortByImportance: boolean;
}

function FileTreeItem({
  node,
  level,
  selectedPath,
  onSelect,
  searchQuery,
  sortByImportance
}: {
  node: FileNode;
  level: number;
  selectedPath: string;
  onSelect: (path: string) => void;
  searchQuery: string;
  sortByImportance: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const isDirectory = node.type === 'directory';
  const isSelected = selectedPath === node.path;

  const handleClick = () => {
    if (isDirectory) {
      setIsOpen(!isOpen);
    } else {
      onSelect(node.path);
    }
  };

  if (searchQuery && !node.name.toLowerCase().includes(searchQuery.toLowerCase()) && !node.path.toLowerCase().includes(searchQuery.toLowerCase())) {
    if (!isDirectory || !node.children?.some(c => c.name.toLowerCase().includes(searchQuery.toLowerCase()))) {
      return null;
    }
  }

  return (
    <div className="select-none">
      <div
        onClick={handleClick}
        className={cn(
          "flex items-center gap-2 py-1 px-2 cursor-pointer transition-colors group",
          isSelected ? "bg-teal-500/10 text-teal-400" : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
        )}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
      >
        {isDirectory && (
          <div className="w-4 h-4 flex items-center justify-center">
            {isOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          </div>
        )}
        {!isDirectory && <div className="w-4 h-4 flex items-center justify-center"><FileCode className="w-3 h-3 opacity-50" /></div>}

        <span className="text-sm truncate flex-1">{node.name}</span>

        {node.importance && node.importance > 0.7 && (
          <div className="w-1 h-1 rounded-full bg-teal-500" title="High Importance" />
        )}
      </div>
      {isDirectory && isOpen && node.children && (
        <div className="mt-0">
          {node.children.map(child => (
            <FileTreeItem
              key={child.id}
              node={child}
              level={level + 1}
              selectedPath={selectedPath}
              onSelect={onSelect}
              searchQuery={searchQuery}
              sortByImportance={sortByImportance}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function FileExplorer({
  nodes,
  selectedPath,
  onSelect,
  searchQuery,
  sortByImportance
}: {
  nodes: FileNode[];
  selectedPath: string;
  onSelect: (path: string) => void;
  searchQuery: string;
  sortByImportance: boolean;
}) {
  const sortedNodes = useMemo(() => {
    if (!sortByImportance) return nodes;
    return [...nodes].sort((a, b) => (b.importance || 0) - (a.importance || 0));
  }, [nodes, sortByImportance]);

  return (
    <div className="flex flex-col h-full bg-zinc-950 border-r border-zinc-800 w-full md:w-72 overflow-hidden">
      <div className="p-4 border-b border-zinc-800">
        <div className="relative group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 group-focus-within:text-teal-500 transition-colors" />
          <input
            type="text"
            placeholder="Search files..."
            aria-label="Search files"
            className="w-full bg-zinc-900 border border-zinc-800 rounded-lg py-2 pl-9 pr-4 text-sm text-zinc-200 focus:outline-none focus:ring-1 focus:ring-teal-500 transition-all"
          />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {sortedNodes.map(node => (
          <FileTreeItem
            key={node.id}
            node={node}
            level={0}
            selectedPath={selectedPath}
            onSelect={onSelect}
            searchQuery={searchQuery}
            sortByImportance={sortByImportance}
          />
        ))}
      </div>
    </div>
  );
}
