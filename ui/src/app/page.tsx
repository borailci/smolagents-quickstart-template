'use client';

import { motion } from 'framer-motion';
import { Sparkles, ArrowDown, Zap, BookOpen, Brain } from 'lucide-react';
import CodebaseCard from '@/components/CodebaseCard';
import { getAllCodebases } from '@/lib/config';

// Animated background orbs
function BackgroundOrbs() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none">
      {/* Purple orb */}
      <motion.div
        className="absolute w-[600px] h-[600px] rounded-full opacity-20"
        style={{
          background: 'radial-gradient(circle, #8B5CF6 0%, transparent 70%)',
          top: '-200px',
          right: '-200px',
        }}
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.2, 0.3, 0.2],
        }}
        transition={{
          duration: 8,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
      {/* Cyan orb */}
      <motion.div
        className="absolute w-[500px] h-[500px] rounded-full opacity-15"
        style={{
          background: 'radial-gradient(circle, #06B6D4 0%, transparent 70%)',
          bottom: '-150px',
          left: '-150px',
        }}
        animate={{
          scale: [1, 1.3, 1],
          opacity: [0.15, 0.25, 0.15],
        }}
        transition={{
          duration: 10,
          repeat: Infinity,
          ease: "easeInOut",
          delay: 2,
        }}
      />
      {/* Pink orb */}
      <motion.div
        className="absolute w-[400px] h-[400px] rounded-full opacity-10"
        style={{
          background: 'radial-gradient(circle, #EC4899 0%, transparent 70%)',
          top: '40%',
          left: '50%',
        }}
        animate={{
          scale: [1, 1.4, 1],
          x: [0, 50, 0],
          opacity: [0.1, 0.2, 0.1],
        }}
        transition={{
          duration: 12,
          repeat: Infinity,
          ease: "easeInOut",
          delay: 4,
        }}
      />
    </div>
  );
}

// Feature cards
function FeatureCards() {
  const features = [
    {
      icon: Brain,
      title: "AI-Powered",
      description: "Multi-agent systems analyze and document codebases",
      color: "#8B5CF6"
    },
    {
      icon: BookOpen,
      title: "Structured Learning",
      description: "Comprehensive tutorials with visual diagrams",
      color: "#06B6D4"
    },
    {
      icon: Zap,
      title: "Interactive",
      description: "Edit and customize tutorials in real-time",
      color: "#EC4899"
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
      {features.map((feature, index) => (
        <motion.div
          key={feature.title}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 + index * 0.1 }}
          whileHover={{ y: -5, scale: 1.02 }}
          className="glass-card p-6 rounded-2xl text-center group"
        >
          <motion.div
            whileHover={{ rotate: 15, scale: 1.1 }}
            className="w-14 h-14 rounded-xl mx-auto mb-4 flex items-center justify-center"
            style={{
              background: `linear-gradient(135deg, ${feature.color}30, ${feature.color}10)`
            }}
          >
            <feature.icon
              className="w-7 h-7"
              style={{ color: feature.color }}
            />
          </motion.div>
          <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            {feature.description}
          </p>
        </motion.div>
      ))}
    </div>
  );
}

export default function HomePage() {
  const codebases = getAllCodebases();

  return (
    <div className="relative min-h-screen">
      <BackgroundOrbs />

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass mb-6"
          >
            <Sparkles className="w-4 h-4 text-violet-500" />
            <span className="text-sm font-medium">AI-Powered Tutorials</span>
          </motion.div>

          {/* Title */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="text-4xl md:text-6xl lg:text-7xl font-bold mb-6"
          >
            <span className="gradient-text">Codebase Tutorial</span>
            <br />
            <span className="text-[hsl(var(--foreground))]">Generator</span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="text-lg md:text-xl text-[hsl(var(--muted-foreground))] max-w-3xl mx-auto mb-8"
          >
            Transform complex codebases into comprehensive, easy-to-follow tutorials
            using AI agents. Click any tutorial below to explore structured learning paths
            with interactive diagrams and editable content.
          </motion.p>

          {/* Scroll indicator */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, y: [0, 10, 0] }}
            transition={{
              opacity: { delay: 1 },
              y: { duration: 1.5, repeat: Infinity, ease: "easeInOut" }
            }}
            className="flex flex-col items-center gap-2 text-[hsl(var(--muted-foreground))]"
          >
            <span className="text-sm">Explore Tutorials</span>
            <ArrowDown className="w-5 h-5" />
          </motion.div>
        </motion.div>

        {/* Features */}
        <FeatureCards />

        {/* Section Title */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="flex items-center gap-4 mb-8"
        >
          <div className="h-px flex-1 bg-gradient-to-r from-transparent to-[hsl(var(--border))]" />
          <h2 className="text-xl font-semibold">Available Tutorials</h2>
          <div className="h-px flex-1 bg-gradient-to-l from-transparent to-[hsl(var(--border))]" />
        </motion.div>

        {/* Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {codebases.map((codebase, index) => (
            <CodebaseCard key={codebase.id} codebase={codebase} index={index} />
          ))}
        </div>

        {/* Empty state */}
        {codebases.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-20"
          >
            <div className="w-20 h-20 rounded-full bg-[hsl(var(--secondary))] flex items-center justify-center mx-auto mb-6">
              <BookOpen className="w-10 h-10 text-[hsl(var(--muted-foreground))]" />
            </div>
            <h3 className="text-xl font-semibold mb-2">No Tutorials Yet</h3>
            <p className="text-[hsl(var(--muted-foreground))]">
              Configure your tutorials in content.yaml to get started.
            </p>
          </motion.div>
        )}

        {/* Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-6"
        >
          {[
            { label: 'Tutorials', value: codebases.length },
            { label: 'Total Modules', value: codebases.reduce((acc, cb) => acc + cb.files.length, 0) },
            { label: 'AI Agents', value: '5+' },
            { label: 'Est. Reading', value: `${codebases.reduce((acc, cb) => acc + cb.files.length * 8, 0)} min` },
          ].map((stat, index) => (
            <motion.div
              key={stat.label}
              whileHover={{ scale: 1.05 }}
              className="text-center p-4 rounded-xl glass-card"
            >
              <div
                className="text-2xl md:text-3xl font-bold gradient-text mb-1"
              >
                {stat.value}
              </div>
              <div className="text-sm text-[hsl(var(--muted-foreground))]">
                {stat.label}
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
