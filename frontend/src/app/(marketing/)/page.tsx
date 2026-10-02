import React from 'react';
import Link from 'next/link';
import { ArrowRight, Code2, Map, MessageSquare, Search, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function LandingPage() {
  return (
    <div className="flex flex-col min-h-screen bg-zinc-950 text-zinc-100 selection:bg-teal-500/30">
      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-6 overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full bg-[radial-gradient(circle_at_center,rgba(20,184,166,0.1)_0%,transparent_70%)] pointer-events-none" />

        <div className="max-w-5xl mx-auto text-center relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-400 text-xs font-medium mb-6">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-teal-500"></span>
            </span>
            Now supporting large-scale repos
          </div>

          <h1 className="text-6xl md:text-7xl font-bold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-b from-white to-zinc-500">
            Get your bearings in <br /> any codebase.
          </h1>

          <p className="text-lg md:text-xl text-zinc-400 mb-10 max-w-2xl mx-auto leading-relaxed">
            Stop spending days reading docs and tracing calls. Greppa maps your repository,
            generates guided tours, and answers complex architectural questions in seconds.
          </p>

          <div className="max-w-2xl mx-auto flex flex-col sm:flex-row gap-3 p-2 rounded-2xl bg-zinc-900/50 border border-zinc-800 backdrop-blur-sm shadow-2xl">
            <Input
              placeholder="https://github.com/owner/repository"
              className="bg-transparent border-none focus-visible:ring-0 text-lg h-12 px-4"
            />
            <Button className="bg-teal-600 hover:bg-teal-500 text-white font-semibold h-12 px-8 rounded-xl transition-all group">
              Analyze
              <ArrowRight className="ml-2 w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Button>
          </div>

          <div className="mt-6 flex flex-wrap justify-center gap-4 text-sm text-zinc-500">
            <span>Try an example:</span>
            <button className="hover:text-teal-400 underline underline-offset-4 transition-colors">facebook/react</button>
            <button className="hover:text-teal-400 underline underline-offset-4 transition-colors">vercel/next.js</button>
            <button className="hover:text-teal-400 underline underline-offset-4 transition-colors">openai/whisper</button>
          </div>
        </div>
      </section>

      {/* How it Works */}
      <section className="py-24 px-6 bg-zinc-900/30">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold mb-4">Orient yourself in minutes</h2>
            <p className="text-zinc-400">Three steps to total codebase clarity.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-12">
            {[
              {
                icon: <Zap className="w-6 h-6 text-teal-500" />,
                title: "Paste a repo",
                desc: "Provide a GitHub URL. Greppa clones the repo, parses the AST, and builds a semantic map of every symbol."
              },
              {
                icon: <Map className="w-6 h-6 text-teal-500" />,
                title: "Take the tour",
                desc: "Follow an AI-generated guided tour that explains the 'why' behind the architecture, not just the 'what'."
              },
              {
                icon: <MessageSquare className="w-6 h-6 text-teal-500" />,
                title: "Ask anything",
                desc: "Use the codebase-aware chat to trace features or find bugs with direct citations to the source code."
              }
            ].map((step, i) => (
              <div key={i} className="group p-8 rounded-3xl bg-zinc-900 border border-zinc-800 hover:border-teal-500/50 transition-all hover:-translate-y-1">
                <div className="w-12 h-12 rounded-2xl bg-zinc-800 flex items-center justify-center mb-6 group-hover:bg-teal-500/10 transition-colors">
                  {step.icon}
                </div>
                <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
                <p className="text-zinc-400 leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-4xl font-bold mb-8 tracking-tight">Engineered for <span className="text-teal-500">large repos</span></h2>
              <div className="space-y-6">
                {[
                  { icon: <Map className="w-5 h-5" />, title: "Architecture Map", desc: "Visualize dependencies and module importance automatically." },
                  { icon: <Code2 className="w-5 h-5" />, title: "Guided Tours", desc: "Curated reading paths for onboarding new developers." },
                  { icon: <MessageSquare className="w-5 h-5" />, title: "Cited Answers", desc: "Every AI response is backed by direct links to the source code." },
                  { icon: <Search className="w-5 h-5" />, title: "First-Issue Finder", desc: "Find the easiest entry points for new contributors." },
                ].map((feat, i) => (
                  <div key={i} className="flex gap-4">
                    <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center text-teal-500">
                      {feat.icon}
                    </div>
                    <div>
                      <h4 className="font-medium mb-1">{feat.title}</h4>
                      <p className="text-zinc-400 text-sm">{feat.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="relative">
              <div className="aspect-square rounded-3xl bg-gradient-to-br from-zinc-800 to-zinc-950 border border-zinc-700 shadow-2xl overflow-hidden group">
                {/* Mock UI Preview */}
                <div className="absolute inset-0 p-4 opacity-50 group-hover:opacity-80 transition-opacity">
                   <div className="w-full h-full bg-zinc-900 rounded-xl border border-zinc-800 p-4 font-mono text-xs text-zinc-500">
                      <div className="flex gap-2 mb-4">
                        <div className="w-3 h-3 rounded-full bg-red-500/50" />
                        <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
                        <div className="w-3 h-3 rounded-full bg-green-500/50" />
                      </div>
                      <div className="space-y-2">
                        <div className="h-4 w-3/4 bg-zinc-800 rounded" />
                        <div className="h-4 w-1/2 bg-zinc-800 rounded" />
                        <div className="h-20 w-full bg-zinc-800/50 rounded border border-zinc-700 p-2 mt-4">
                           <div className="h-2 w-1/3 bg-teal-500/30 rounded mb-2" />
                           <div className="h-2 w-2/3 bg-zinc-700 rounded mb-2" />
                           <div className="h-2 w-1/2 bg-zinc-700 rounded" />
                        </div>
                        <div className="h-4 w-3/4 bg-zinc-800 rounded mt-4" />
                      </div>
                   </div>
                </div>
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="bg-teal-600 text-white px-4 py-2 rounded-full text-sm font-bold shadow-xl animate-bounce">
                    Interactive Tour Preview
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-zinc-900 bg-zinc-950">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-teal-600 rounded-lg flex items-center justify-center font-bold text-white">G</div>
            <span className="font-bold text-xl tracking-tight">Greppa</span>
          </div>
          <div className="flex gap-8 text-sm text-zinc-500">
            <Link href="#" className="hover:text-zinc-300 transition-colors">GitHub</Link>
            <Link href="#" className="hover:text-zinc-300 transition-colors">Twitter</Link>
            <Link href="#" className="hover:text-zinc-300 transition-colors">Privacy</Link>
          </div>
          <p className="text-sm text-zinc-600">© 2026 Greppa AI. Get your bearings.</p>
        </div>
      </footer>
    </div>
  );
}
