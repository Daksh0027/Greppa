'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, X, Search, Folder, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSend: (query: string) => void;
  isSending: boolean;
}

export default function ChatInput({ onSend, isSending }: ChatInputProps) {
  const [query, setQuery] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (query.trim()) {
        onSend(query);
        setQuery('');
      }
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [query]);

  return (
    <div className="relative group">
      <textarea
        ref={textareaRef}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask Greppa about the codebase..."
        className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl py-4 pl-4 pr-14 text-zinc-200 focus:outline-none focus:ring-2 focus:ring-teal-500/50 transition-all resize-none overflow-hidden max-h-48 shadow-2xl"
        rows={1}
      />
      <div className="absolute right-3 bottom-3">
        <Button
          disabled={!query.trim() || isSending}
          onClick={() => {
            onSend(query);
            setQuery('');
          }}
          className="bg-teal-600 hover:bg-teal-500 text-white h-9 w-9 p-0 rounded-xl transition-all"
        >
          {isSending ? (
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </Button>
      </div>
    </div>
  );
}
