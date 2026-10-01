"use client";

import React, { useRef, useEffect } from "react";
import Editor, { OnMount } from "@monaco-editor/react";
import { FileCode, Layers } from "lucide-react";

interface CodeViewerProps {
  code: string;
  filePath: string;
  language: string;
  highlightRange?: { startLine: number; endLine: number } | null;
  symbols?: Array<{ name: string; kind: string; start_line: number; end_line: number; importance: number }>;
  onSelectSymbol?: (sym: any) => void;
}

export default function CodeViewer({
  code,
  filePath,
  language,
  highlightRange,
  symbols = [],
  onSelectSymbol,
}: CodeViewerProps) {
  const editorRef = useRef<any>(null);
  const monacoRef = useRef<any>(null);
  const decorationsRef = useRef<any[]>([]);

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
  };

  useEffect(() => {
    if (editorRef.current && highlightRange && highlightRange.startLine) {
      editorRef.current.revealLineInCenter(highlightRange.startLine);
      if (monacoRef.current) {
        decorationsRef.current = editorRef.current.deltaDecorations(
          decorationsRef.current,
          [
            {
              range: new monacoRef.current.Range(
                highlightRange.startLine,
                1,
                highlightRange.endLine || highlightRange.startLine,
                1
              ),
              options: {
                isWholeLine: true,
                className: "bg-blue-500/20 border-l-4 border-blue-400",
                linesDecorationsClassName: "monaco-highlight-gutter",
              },
            },
          ]
        );
      }
    }
  }, [highlightRange]);

  const mapMonacoLanguage = (lang: string) => {
    switch (lang?.toLowerCase()) {
      case "python":
        return "python";
      case "javascript":
        return "javascript";
      case "typescript":
        return "typescript";
      case "go":
        return "go";
      case "rust":
        return "rust";
      case "java":
        return "java";
      case "json":
        return "json";
      case "markdown":
        return "markdown";
      default:
        return "plaintext";
    }
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden shadow-lg">
      <div className="flex items-center justify-between px-4 py-2 bg-zinc-900 border-b border-zinc-800 text-xs">
        <div className="flex items-center gap-2 text-zinc-300">
          <FileCode size={16} className="text-blue-400" />
          <span className="font-mono font-medium">{filePath || "No file selected"}</span>
          {highlightRange && (
            <span className="bg-blue-600/30 text-blue-300 px-2 py-0.5 rounded text-[11px] font-mono">
              Lines {highlightRange.startLine}-{highlightRange.endLine}
            </span>
          )}
        </div>

        {symbols.length > 0 && (
          <div className="flex items-center gap-1.5 overflow-x-auto max-w-[50%]">
            <span className="text-zinc-500 flex items-center gap-1 text-[11px]">
              <Layers size={12} /> AST Symbols:
            </span>
            {symbols.slice(0, 5).map((s, idx) => (
              <button
                key={idx}
                onClick={() => onSelectSymbol && onSelectSymbol(s)}
                className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-2 py-0.5 rounded text-[11px] font-mono truncate transition"
                title={`${s.kind}: ${s.name} (line ${s.start_line})`}
              >
                {s.name}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1 w-full h-[500px]">
        <Editor
          height="100%"
          language={mapMonacoLanguage(language)}
          value={code || "// Select a search result or file to view source code"}
          theme="vs-dark"
          options={{
            readOnly: true,
            minimap: { enabled: true },
            fontSize: 13,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            automaticLayout: true,
            renderWhitespace: "selection",
          }}
          onMount={handleEditorDidMount}
        />
      </div>
    </div>
  );
}
