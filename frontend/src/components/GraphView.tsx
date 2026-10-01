"use client";

import React, { useMemo, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { GitBranch, Activity, Code2 } from "lucide-react";

const SymbolCustomNode = ({ data }: NodeProps) => {
  const getKindColor = (kind: string) => {
    switch (kind?.toLowerCase()) {
      case "class":
        return "border-purple-500 bg-purple-950/60 text-purple-200";
      case "function":
        return "border-blue-500 bg-blue-950/60 text-blue-200";
      case "method":
        return "border-emerald-500 bg-emerald-950/60 text-emerald-200";
      default:
        return "border-zinc-600 bg-zinc-900 text-zinc-200";
    }
  };

  return (
    <div
      className={`px-3 py-2 rounded-lg border shadow-md min-w-[160px] text-xs transition-all hover:scale-105 cursor-pointer ${getKindColor(
        data.kind as string
      )}`}
    >
      <Handle type="target" position={Position.Top} className="w-2 h-2 bg-blue-400" />
      <div className="flex items-center justify-between gap-1.5 mb-1">
        <span className="font-semibold truncate">{data.label as string}</span>
        <span className="text-[10px] uppercase font-mono px-1 py-0.2 bg-black/40 rounded">
          {data.kind as string}
        </span>
      </div>
      <div className="flex items-center justify-between text-[11px] opacity-80">
        <span className="truncate max-w-[90px]">{data.file_path as string}</span>
        <span className="font-mono text-amber-300">★ {data.importance as number}</span>
      </div>
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 bg-purple-400" />
    </div>
  );
};

interface GraphViewProps {
  nodes: any[];
  edges: any[];
  onSelectSymbol?: (symbolData: any) => void;
}

export default function GraphView({ nodes: initialNodes, edges: initialEdges, onSelectSymbol }: GraphViewProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes || []);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges || []);

  React.useEffect(() => {
    setNodes(initialNodes || []);
    setEdges(initialEdges || []);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const nodeTypes = useMemo(() => ({ symbolNode: SymbolCustomNode }), []);

  const handleNodeClick = useCallback(
    (_: any, node: any) => {
      if (onSelectSymbol) {
        onSelectSymbol(node.data);
      }
    },
    [onSelectSymbol]
  );

  return (
    <div className="w-full h-full min-h-[500px] bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden relative shadow-lg">
      <div className="absolute top-3 left-3 z-10 bg-zinc-900/90 backdrop-blur border border-zinc-800 px-3 py-1.5 rounded-lg text-xs flex items-center gap-3 shadow">
        <div className="flex items-center gap-1.5 text-zinc-300">
          <GitBranch size={14} className="text-blue-400" />
          <span>AST Architecture Graph ({nodes.length} symbols, {edges.length} edges)</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-zinc-400 border-l border-zinc-700 pl-3">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span> Functions</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-purple-500"></span> Classes</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500"></span> Methods</span>
        </div>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        fitView
      >
        <Background color="#27272a" gap={16} />
        <Controls className="bg-zinc-900 border-zinc-800 text-zinc-300" />
        <MiniMap
          nodeColor="#3b82f6"
          maskColor="rgba(0, 0, 0, 0.7)"
          className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden"
        />
      </ReactFlow>
    </div>
  );
}
