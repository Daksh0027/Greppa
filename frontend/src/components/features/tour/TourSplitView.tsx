'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  SkipForward,
  MessageSquare,
  Zap,
  Info
} from 'lucide-react';
import Editor, { Monaco } from '@monaco-editor/react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

interface TourStep {
  step_order: number;
  file_path: string;
  start_line: number;
  end_line: number;
  title: string;
  why_it_matters: string;
  body: string;
}

interface TourSplitViewProps {
  steps: TourStep[];
  currentStepIndex: number;
  onStepChange: (index: number) => void;
  onAskAboutStep: (step: TourStep) => void;
}

export default function TourSplitView({
  steps,
  currentStepIndex,
  onStepChange,
  onAskAboutStep
}: TourSplitViewProps) {
  const editorRef = useRef<any>(null);
  const step = steps[currentStepIndex];

  useEffect(() => {
    if (editorRef.current && step) {
      const editor = editorRef.current;

      // Scroll to the range
      editor.revealLine(step.start_line);

      // Highlight the range using deltaDecorations
      // In a real app, we'd manage the decorations array to clear previous ones
      const decorations = editor.deltaDecorations([], [
        {
          range: new (window as any).monaco.Range(
            step.start_line,
            1,
            step.end_line,
            1
          ),
          options: {
            isWholeLine: true,
            className: 'tour-highlight-bg',
          },
        },
      ]);
    }
  }, [step]);

  if (!step) return null;

  return (
    <div className="flex h-full w-full overflow-hidden bg-zinc-950 flex-col md:flex-row">
      {/* Left: Explanation Panel (40%) */}
      <div className="w-full md:w-[40%] flex flex-col border-b md:border-b-0 md:border-r border-zinc-800 bg-zinc-900/30 overflow-y-auto">
        <div className="p-8 space-y-8">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-widest text-zinc-500">
              Step {currentStepIndex + 1} of {steps.length}
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onStepChange(currentStepIndex - 1)}
                disabled={currentStepIndex === 0}
                className="h-8 w-8 p-0"
                aria-label="Previous Step"
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onStepChange(currentStepIndex + 1)}
                disabled={currentStepIndex === steps.length - 1}
                className="h-8 w-8 p-0"
                aria-label="Next Step"
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>

          <div>
            <h2 className="text-3xl font-bold text-white mb-4">{step.title}</h2>
            <div className="prose prose-invert max-w-none">
              <p className="text-zinc-400 leading-relaxed text-lg">
                {step.body}
              </p>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-teal-500/10 border border-teal-500/20">
            <div className="flex items-center gap-2 text-teal-500 text-sm font-bold mb-3">
              <Zap className="w-4 h-4" />
              WHY THIS MATTERS
            </div>
            <p className="text-zinc-300 text-sm leading-relaxed">
              {step.why_it_matters}
            </p>
          </div>

          <div className="flex gap-3 pt-8">
            <Button
              onClick={() => onAskAboutStep(step)}
              className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl gap-2"
            >
              <MessageSquare className="w-4 h-4" />
              Ask about this step
            </Button>
            <Button
              variant="outline"
              onClick={() => onStepChange(steps.length - 1)}
              className="border-zinc-800 text-zinc-400 rounded-xl"
            >
              <SkipForward className="w-4 h-4 mr-2" />
              Skip Tour
            </Button>
          </div>
        </div>
      </div>

      {/* Right: Code View (60%) */}
      <div className="w-[60%] flex flex-col relative">
        <div className="h-12 border-b border-zinc-800 flex items-center px-4 bg-zinc-900/50 justify-between">
          <div className="flex items-center gap-2 text-sm font-mono text-zinc-500">
            <Info className="w-4 h-4 text-teal-500" />
            {step.file_path}
          </div>
        </div>
        <div className="flex-1">
          <Editor
            height="100%"
            theme="vs-dark"
            path={step.file_path}
            defaultLanguage="typescript"
            options={{
              readOnly: true,
              fontSize: 14,
              fontFamily: 'JetBrains Mono, monospace',
              minimap: { enabled: false },
              lineNumbers: 'on',
              glyphMargin: false,
              folding: false,
              scrollBeyondLastLine: false,
              padding: { top: 20 },
            }}
            onMount={(editor, monaco) => {
              editorRef.current = editor;
            }}
          />
        </div>
      </div>
    </div>
  );
}
