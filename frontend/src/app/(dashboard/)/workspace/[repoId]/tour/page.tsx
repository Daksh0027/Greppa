'use client';

import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api/client';
import { Tour, TourStep } from '@/types';
import TourSplitView from '@/components/features/tour/TourSplitView';
import { Progress } from '@/components/ui/progress';
import { Loader2 } from 'lucide-react';

export default function TourPage() {
  const params = useParams();
  const router = useRouter();
  const repoId = params.repoId as string;

  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);

  const { data: tours, isLoading, error } = useQuery({
    queryKey: ['tours', repoId],
    queryFn: () => api.listTours(repoId),
  });

  const tour = tours?.[0]; // Default to the first tour (Big Picture)

  useEffect(() => {
    // Sync current step with URL if needed
    const searchParams = new URLSearchParams(window.location.search);
    const step = searchParams.get('step');
    if (step) {
      setCurrentStepIndex(parseInt(step) - 1);
    }
  }, []);

  const handleStepChange = (index: number) => {
    setCurrentStepIndex(index);
    const searchParams = new URLSearchParams(window.location.search);
    searchParams.set('step', (index + 1).toString());
    router.push(`?${searchParams.toString()}`, { scroll: false });
  };

  const handleGenerateCustomTour = async (query: string) => {
    setIsGenerating(true);
    try {
      await api.generateTour(repoId, 'feature_trace', { feature_query: query });
      // In a real app, we'd poll until the tour is ready
    } catch (e) {
      console.error(e);
    } finally {
      setIsGenerating(false);
    }
  };

  if (isLoading) return <div className="h-screen flex items-center justify-center bg-zinc-950"><Loader2 className="w-8 h-8 animate-spin text-teal-500" /></div>;
  if (error || !tour) return <div className="h-screen flex items-center justify-center bg-zinc-950 text-zinc-500">No tour available for this repository.</div>;

  return (
    <div className="h-[calc(100vh-64px)] flex flex-col bg-zinc-950 overflow-hidden">
      {/* Top Progress Bar */}
      <div className="h-1 w-full bg-zinc-800">
        <Progress
          value={((currentStepIndex + 1) / tour.steps.length) * 100}
          className="h-full bg-transparent"
          indicatorClassName="bg-teal-500"
        />
      </div>

      {/* Custom Tour Trigger */}
      <div className="px-6 py-3 bg-zinc-900/50 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-3 text-sm text-zinc-400">
          <span className="font-medium">Current Tour:</span>
          <span className="text-white font-bold">{tour.title}</span>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Trace a feature (e.g. 'how does auth work?')"
            className="bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-1.5 text-xs text-zinc-300 focus:outline-none focus:ring-1 focus:ring-teal-500 w-64"
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleGenerateCustomTour(e.currentTarget.value);
            }}
          />
          <Button
            size="sm"
            disabled={isGenerating}
            className="bg-teal-600 hover:bg-teal-500 h-8 px-3 text-xs rounded-lg"
            onClick={() => handleGenerateCustomTour('custom')}
          >
            {isGenerating ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Generate'}
          </Button>
        </div>
      </div>

      <div className="flex-1">
        <TourSplitView
          steps={tour.steps}
          currentStepIndex={currentStepIndex}
          onStepChange={handleStepChange}
          onAskAboutStep={(step) => {
            router.push(`/repo/${repoId}/chat?query=Explain the purpose of ${step.file_path} in this step`);
          }}
        />
      </div>
    </div>
  );
}
