'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { CodebaseCard } from '@/components/CodebaseCard';
import { LoadingProgress } from '@/components/LoadingProgress';

interface Tutorial {
  filename: string;
  title: string;
}

interface Codebase {
  id: string;
  name: string;
  description: string;
  tutorialCount: number;
  tutorials: Tutorial[];
}

// Map codebase names to icons and colors
const codebaseStyles: Record<string, { icon: string; color: string }> = {
  deepagents: { icon: 'robot', color: '#8B5CF6' },
  default: { icon: 'code', color: '#06B6D4' },
};

export default function Home() {
  const router = useRouter();
  const [codebases, setCodebases] = useState<Codebase[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedCodebase, setSelectedCodebase] = useState<Codebase | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/codebases')
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          setError(data.error);
        } else {
          setCodebases(data.codebases || []);
        }
      })
      .catch(err => setError(err.message));
  }, []);

  const handleCardClick = (codebase: Codebase) => {
    setSelectedCodebase(codebase);
    setLoading(true);
  };

  const handleLoadingComplete = () => {
    if (selectedCodebase) {
      router.push(`/tutorial/${selectedCodebase.id}`);
    }
  };

  const getStyle = (id: string) => codebaseStyles[id] || codebaseStyles.default;

  return (
    <>
      <AnimatePresence>
        {loading && selectedCodebase && (
          <LoadingProgress
            accentColor={getStyle(selectedCodebase.id).color}
            onComplete={handleLoadingComplete}
          />
        )}
      </AnimatePresence>

      <div className="container mx-auto px-6 py-12">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12 text-center"
        >
          <h2 className="mb-4 text-4xl font-bold">
            <span className="bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
              Explore Tutorials
            </span>
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-slate-400">
            AI-generated tutorials from your codebases. Click a card to start learning.
          </p>
        </motion.div>

        {/* Error state */}
        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mb-8 rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-center text-red-400"
          >
            {error}
          </motion.div>
        )}

        {/* Cards Grid */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {codebases.map((codebase, index) => (
            <CodebaseCard
              key={codebase.id}
              codebase={{
                ...codebase,
                icon: getStyle(codebase.id).icon,
                color: getStyle(codebase.id).color,
                files: codebase.tutorials.map(t => ({ path: t.filename, title: t.title })),
              }}
              index={index}
              onClick={() => handleCardClick(codebase)}
            />
          ))}
        </div>

        {/* Empty state */}
        {!error && codebases.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="py-20 text-center"
          >
            <p className="text-slate-500">
              No tutorials found. Run <code className="text-cyan-400">deep-agent</code> to generate some!
            </p>
          </motion.div>
        )}
      </div>
    </>
  );
}
