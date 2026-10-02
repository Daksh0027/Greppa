'use client';

import React from 'react';
import { Citation } from '@/types';
import { FileCode, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface CitationLinkProps {
  citation: Citation;
  onOpen: (citation: Citation) => void;
  className?: string;
}

export default function CitationLink({ citation, onOpen, className }: CitationLinkProps) {
  return (
    <button
      onClick={() => onOpen(citation)}
      className={cn(
        "inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-teal-500/10 text-teal-400 border border-teal-500/20 text-xs font-mono hover:bg-teal-500/20 transition-colors",
        className
      )}
    >
      <FileCode className="w-3 h-3" />
      <span>
        {citation.file_path}:{citation.start_line}-{citation.end_line}
      </span>
    </button>
  );
}
