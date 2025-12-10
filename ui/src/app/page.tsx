import { getContentConfig } from "@/lib/config";
import { CodebaseCard } from "@/components/CodebaseCard";
import { Sparkles } from "lucide-react";

export default function Home() {
  const config = getContentConfig();

  return (
    <div className="container mx-auto px-4 py-12">
      <div className="mb-16 text-center space-y-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400 text-sm mb-4">
          <Sparkles className="w-4 h-4" />
          <span>AI-Powered Documentation</span>
        </div>
        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight">
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-white via-purple-200 to-cyan-200">
            Explore Codebase Tutorials
          </span>
        </h1>
        <p className="text-xl text-gray-400 max-w-2xl mx-auto">
          Select a project below to generate and interact with an AI-curated interactive walkthrough.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {config.codebases.map((codebase) => (
          <CodebaseCard key={codebase.id} codebase={codebase} />
        ))}
      </div>
    </div>
  );
}
