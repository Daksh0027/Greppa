'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import { Message, Citation } from '@/types';
import { StreamChunk } from '@/lib/api/types';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import { Bot, Search, Folder, FileText, X, Maximize2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import Editor from '@monaco-editor/react';

export default function ChatLayout() {
  const params = useParams();
  const router = useRouter();
  const repoId = params.repoId as string;

  const [messages, setMessages] = useState<Message[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (query: string) => {
    if (!query.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      createdAt: new Date(),
    };

    setMessages(prev => [...prev, userMsg]);
    setIsSending(true);

    try {
      const assistantMsgId = (Date.now() + 1).toString();
      let fullContent = '';
      const citations: Citation[] = [];
      const steps: any[] = [];

      // Add placeholder assistant message
      setMessages(prev => [...prev, {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        createdAt: new Date(),
      }]);

      const stream = await api.askAgentStream(repoId, query);

      for await (const chunk of stream) {
        if (chunk.type === 'text') {
          fullContent += chunk.content;
          setMessages(prev => prev.map(m =>
            m.id === assistantMsgId ? { ...m, content: fullContent } : m
          ));
        } else if (chunk.type === 'citation') {
          citations.push(chunk.citation);
        } else if (chunk.type === 'step') {
          steps.push(chunk.step);
        }
      }

      setMessages(prev => prev.map(m =>
        m.id === assistantMsgId ? { ...m, content: fullContent, citations, steps } : m
      ));
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setIsSending(false);
    }
  };

  const handleCitationClick = (citation: Citation) => {
    setSelectedCitation(citation);
  };

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-zinc-950">
      {/* Session Drawer (Left) */}
      <div className="w-64 border-r border-zinc-800 bg-zinc-900/50 hidden lg:flex flex-col">
        <div className="p-4 border-b border-zinc-800">
          <Button className="w-full bg-teal-600 hover:bg-teal-500 text-white rounded-xl h-10 text-sm font-bold">
            New Chat
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          <div className="text-xs font-bold text-zinc-500 uppercase px-2 mb-2">Recent Sessions</div>
          <div className="p-2 rounded-lg bg-zinc-800 text-zinc-200 text-sm cursor-pointer border border-teal-500/30">
            Understanding Auth Flow
          </div>
          <div className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 text-sm cursor-pointer transition-colors">
            Database Schema Review
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative min-w-0">
        {/* Chat Header */}
        <div className="h-12 border-b border-zinc-800 flex items-center justify-between px-4 bg-zinc-900/50">
          <div className="flex items-center gap-2 text-sm text-zinc-400 truncate">
            <Bot className="w-4 h-4 text-teal-500" />
            <span className="font-medium">Greppa AI</span>
            <span className="text-zinc-600">/ {repoId}</span>
          </div>
          <div className="flex items-center gap-2">
            <select className="bg-zinc-950 border border-zinc-800 rounded-lg px-2 py-1 text-xs text-zinc-400 focus:outline-none focus:ring-1 focus:ring-teal-500">
              <option>Whole Repo</option>
              <option>src/api</option>
              <option>src/core</option>
            </select>
          </div>
        </div>

        {/* Messages List */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth"
        >
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-xl mx-auto space-y-8">
              <div className="w-20 h-20 rounded-3xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center">
                <Bot className="w-10 h-10 text-teal-500" />
              </div>
              <div>
                <h2 className="text-3xl font-bold text-white mb-3">How can I help you?</h2>
                <p className="text-zinc-400 leading-relaxed">
                  I've analyzed this repository. You can ask me about the architecture, trace a specific feature, or find a bug.
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full">
                {[
                  "How does authentication work end-to-end?",
                  "What are the main entry points of this app?",
                  "Explain the data flow for a user request.",
                  "Where is the database schema defined?"
                ].map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(q)}
                    className="p-4 rounded-2xl bg-zinc-900 border border-zinc-800 text-left text-sm text-zinc-400 hover:bg-zinc-800 hover:text-white hover:border-teal-500/50 transition-all"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map(msg => (
              <ChatMessage
                key={msg.id}
                message={msg}
                onCitationClick={handleCitationClick}
              />
            ))
          )}
          {isSending && (
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full bg-teal-600 flex items-center justify-center shrink-0">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="bg-zinc-900 border border-zinc-800 p-4 rounded-2xl rounded-tl-none">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-zinc-600 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-zinc-600 rounded-full animate-bounce [animation-delay:0.2s]" />
                  <div className="w-2 h-2 bg-zinc-600 rounded-full animate-bounce [animation-delay:0.4s]" />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-6 bg-gradient-to-t from-zinc-950 via-zinc-950 to-transparent">
          <div className="max-w-4xl mx-auto">
            <ChatInput onSend={handleSend} isSending={isSending} />
            <p className="text-center text-[10px] text-zinc-600 mt-3">
              Greppa may make mistakes. Check citations to verify information.
            </p>
          </div>
        </div>
      </div>

      {/* Citation Slide-over Panel */}
      {selectedCitation && (
        <div className="fixed inset-y-0 right-0 w-full max-w-2xl bg-zinc-900 border-l border-zinc-800 shadow-2xl flex flex-col animate-in slide-in-from-right duration-300 z-50">
          <div className="p-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/50">
            <div className="flex items-center gap-3">
              <FileText className="w-4 h-4 text-teal-500" />
              <span className="text-sm font-mono text-zinc-300">{selectedCitation.file_path}</span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                asChild
                className="text-xs text-teal-500 hover:text-teal-400"
              >
                <Link href={`/repo/${repoId}/explore?file=${selectedCitation.file_path}`}>
                  Open in Explorer
                </Link>
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setSelectedCitation(null)} className="h-8 w-8 p-0">
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>
          <div className="flex-1 overflow-hidden">
            <Editor
              height="100%"
              theme="vs-dark"
              path={selectedCitation.file_path}
              defaultLanguage="typescript"
              options={{
                readOnly: true,
                fontSize: 14,
                fontFamily: 'JetBrains Mono, monospace',
                minimap: { enabled: false },
                padding: { top: 20 },
              }}
              onMount={(editor) => {
                editor.revealLine(selectedCitation.start_line);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
