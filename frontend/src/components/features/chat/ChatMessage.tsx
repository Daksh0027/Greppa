'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message, AgentStep } from '@/types';
import CitationLink from './CitationLink';
import { User, Bot, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatMessageProps {
  message: Message;
  onCitationClick: (citation: any) => void;
}

export default function ChatMessage({ message, onCitationClick }: ChatMessageProps) {
  const isAssistant = message.role === 'assistant';
  const [isThoughtExpanded, setIsThoughtExpanded] = React.useState(false);

  return (
    <div className={cn(
      "flex w-full gap-4 mb-8 animate-in fade-in slide-in-from-bottom-2",
      isAssistant ? "flex-row" : "flex-row-reverse"
    )}>
      <div className={cn(
        "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
        isAssistant ? "bg-teal-600 text-white" : "bg-zinc-800 text-zinc-400"
      )}>
        {isAssistant ? <Bot className="w-5 h-5" /> : <User className="w-5 h-5" />}
      </div>

      <div className={cn(
        "flex flex-col max-w-[80%]",
        isAssistant ? "items-start" : "items-end"
      )}>
        <div className={cn(
          "p-4 rounded-2xl leading-relaxed",
          isAssistant
            ? "bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-tl-none"
            : "bg-teal-600 text-white rounded-tr-none"
        )}>
          {/* Agent Thought Process */}
          {isAssistant && message.steps && message.steps.length > 0 && (
            <div className="mb-4 border-b border-zinc-800 pb-3">
              <button
                onClick={() => setIsThoughtExpanded(!isThoughtExpanded)}
                className="flex items-center gap-2 text-xs font-bold text-zinc-500 uppercase tracking-widest hover:text-zinc-300 transition-colors"
              >
                {isThoughtExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                {isThoughtExpanded ? 'Hide reasoning' : 'View reasoning'}
              </button>
              {isThoughtExpanded && (
                <div className="mt-3 space-y-3">
                  {message.steps.map((step, i) => (
                    <div key={i} className="text-xs p-2 rounded bg-zinc-950 border border-zinc-800 text-zinc-400">
                      <span className="font-bold text-teal-500 mr-2">Step {step.step_number}:</span>
                      {step.thought}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
              code: ({ node, inline, className, children, ...props }) => {
                return (
                  <code className={cn("bg-zinc-950 px-1 rounded text-teal-400 font-mono", className)} {...props}>
                    {children}
                  </code>
                );
              }
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Citations */}
        {isAssistant && message.citations && message.citations.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {message.citations.map((citation, i) => (
              <CitationLink
                key={i}
                citation={citation}
                onOpen={onCitationClick}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
