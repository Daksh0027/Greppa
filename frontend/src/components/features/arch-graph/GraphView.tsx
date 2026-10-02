'use client';

import React, { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  ConnectionMode,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { ArchGraph } from '@/types';
import { cn } from '@/lib/utils';

interface GraphNodeProps {
  data: {
    label: string;
    kind: string;
    importance: number;
    file_path: string;
    onClick: (node: any) => void;
  };
}

const CustomNode = ({ data }: GraphNodeProps) => {
  const size = Math.max(40, Math.min(120, data.importance * 10));

  const getColor = (kind: string) => {
    switch (kind) {
      case 'class': return 'border-teal-500 text-teal-400 bg-teal-500/10';
      case 'function': return 'border-blue-500 text-blue-400 bg-blue-500/10';
      case 'module': return 'border-purple-500 text-purple-400 bg-purple-500/10';
      default: return 'border-zinc-500 text-zinc-400 bg-zinc-500/10';
    }
  };

  return (
    <div
      className={cn(
        "px-3 py-2 rounded-xl border-2 shadow-lg transition-all hover:scale-105 cursor-pointer",
        getColor(data.kind)
      )}
      style={{ width: size * 2 }}
      onClick={() => data.onClick(data)}
    >
      <Handle type="target" position={Position.Top} className="w-2 h-2 bg-zinc-600" />
      <div className="text-center">
        <div className="text-xs font-bold truncate">{data.label}</div>
        <div className="text-[10px] opacity-60 truncate">{data.file_path}</div>
      </div>
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 bg-zinc-600" />
    </div>
  );
};

const nodeTypes = {
  greppaNode: CustomNode,
};

export default function GraphView({
  data,
  onNodeClick
}: {
  data: ArchGraph;
  onNodeClick: (node: any) => void
}) {
  const initialNodes = useMemo(() => {
    return data.nodes.map((node, i) => ({
      id: node.id,
      type: 'greppaNode',
      position: {
        x: Math.random() * 800,
        y: Math.random() * 600
      },
      data: { ...node, onClick: onNodeClick },
    }));
  }, [data, onNodeClick]);

  const initialEdges = useMemo(() => {
    return data.edges.map((edge, i) => ({
      id: `e${i}`,
      source: edge.source,
      target: edge.target,
      label: edge.edge_type,
      animated: edge.edge_type === 'calls',
      style: { stroke: '#525252', strokeWidth: edge.weight || 1 },
    }));
  }, [data]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div className="w-full h-full bg-zinc-950 rounded-3xl border border-zinc-800 overflow-hidden relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
      >
        <Background color="#27272a" gap={20} />
        <Controls className="bg-zinc-900 border-zinc-800 fill-white" />
        <MiniMap
          nodeColor={(n) => {
            const node = data.nodes.find(node => node.id === n.id);
            if (node?.kind === 'class') return '#14b8a6';
            if (node?.kind === 'function') return '#3b82f6';
            return '#71717a';
          }}
          className="bg-zinc-900 border border-zinc-800"
        />
      </ReactFlow>
    </div>
  );
}
