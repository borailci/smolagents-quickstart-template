"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import { Loader2, CheckCircle2, Terminal, Cpu, Database } from "lucide-react";

interface LoadingProgressProps {
    message?: string;
    onComplete?: () => void;
    accentColor?: string;
}

const STEPS = [
    { text: "Initializing quantum agents...", icon: Cpu },
    { text: "Parsing neural syntax trees...", icon: NetworkIcon },
    { text: "Optimizing knowledge graph...", icon: Database },
    { text: "Synthesizing tutorial matrix...", icon: Terminal },
];

function NetworkIcon(props: any) {
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            {...props}
        >
            <rect x="16" y="16" width="6" height="6" rx="1" />
            <rect x="2" y="16" width="6" height="6" rx="1" />
            <rect x="9" y="2" width="6" height="6" rx="1" />
            <path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3" />
            <path d="M12 12V8" />
        </svg>
    );
}

export function LoadingProgress({ onComplete, accentColor = "#8B5CF6" }: LoadingProgressProps) {
    const [progress, setProgress] = useState(0);
    const [stepIndex, setStepIndex] = useState(0);
    const duration = parseInt(process.env.NEXT_PUBLIC_LOADING_DURATION_MS || "3500");

    useEffect(() => {
        const startTime = Date.now();
        const interval = setInterval(() => {
            const elapsed = Date.now() - startTime;
            const newProgress = Math.min((elapsed / duration) * 100, 100);

            setProgress(newProgress);

            const totalSteps = STEPS.length;
            const currentStep = Math.min(Math.floor((newProgress / 100) * totalSteps), totalSteps - 1);
            setStepIndex(currentStep);

            if (newProgress >= 100) {
                clearInterval(interval);
                setTimeout(() => {
                    onComplete?.();
                }, 800);
            }
        }, 16);

        return () => clearInterval(interval);
    }, [duration, onComplete]);

    const CurrentIcon = STEPS[stepIndex].icon;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-[#050510]"
            >
                {/* Animated Background Grid */}
                <div className="absolute inset-0 opacity-20 pointer-events-none"
                    style={{
                        backgroundImage: `radial-gradient(circle at center, ${accentColor}20 1px, transparent 1px)`,
                        backgroundSize: '40px 40px'
                    }}
                />

                <div className="relative w-full max-w-2xl p-12 flex flex-col items-center">
                    {/* Main Visualizer */}
                    <div className="relative w-64 h-64 mb-12 flex items-center justify-center">
                        {/* Outer Rotating Ring */}
                        <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
                            className="absolute inset-0 rounded-full border border-dashed border-white/20"
                        />

                        {/* Inner Counter-Rotating Ring */}
                        <motion.div
                            animate={{ rotate: -360 }}
                            transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
                            className="absolute inset-4 rounded-full border border-white/10"
                        />

                        {/* Progress Circle (Glow) */}
                        <svg className="absolute inset-0 w-full h-full rotate-[-90deg]" viewBox="0 0 100 100">
                            <circle cx="50" cy="50" r="48" fill="none" stroke="#ffffff05" strokeWidth="1" />
                            <motion.circle
                                cx="50" cy="50" r="48"
                                fill="none"
                                stroke={accentColor}
                                strokeWidth="2"
                                strokeLinecap="round"
                                strokeDasharray="301"
                                initial={{ strokeDashoffset: 301 }}
                                animate={{ strokeDashoffset: 301 - (301 * progress) / 100 }}
                                transition={{ ease: "linear", duration: 0.1 }}
                                style={{ filter: `drop-shadow(0 0 8px ${accentColor})` }}
                            />
                        </svg>

                        {/* Central AI Core */}
                        <div className="relative z-10 flex flex-col items-center justify-center">
                            <motion.div
                                key={stepIndex}
                                initial={{ scale: 0.8, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                exit={{ scale: 0.8, opacity: 0 }}
                                transition={{ type: "spring", bounce: 0.5 }}
                            >
                                <CurrentIcon className="w-16 h-16 text-white" style={{ filter: `drop-shadow(0 0 10px ${accentColor})` }} />
                            </motion.div>
                            <div className="mt-4 text-3xl font-mono font-bold text-white tracking-widest">
                                {Math.round(progress)}
                                <span className="text-sm text-gray-500 ml-1">%</span>
                            </div>
                        </div>
                    </div>

                    {/* Status Text with Glitch Effect */}
                    <div className="h-16 flex flex-col items-center justify-center w-full">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={stepIndex}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                className="flex flex-col items-center gap-2"
                            >
                                <h2 className="text-2xl font-light text-white tracking-wider uppercase">
                                    {STEPS[stepIndex].text}
                                </h2>
                                <div className="flex gap-1">
                                    {[...Array(3)].map((_, i) => (
                                        <motion.div
                                            key={i}
                                            animate={{ opacity: [0.3, 1, 0.3] }}
                                            transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
                                            className="w-2 h-2 rounded-full"
                                            style={{ backgroundColor: accentColor }}
                                        />
                                    ))}
                                </div>
                            </motion.div>
                        </AnimatePresence>
                    </div>

                    {/* Terminal Output Decoration */}
                    <div className="mt-8 font-mono text-xs text-gray-600 flex flex-col items-center gap-1 opacity-50">
                        <p>{`> SYSTEM.INIT_SEQUENCE_START`}</p>
                        <p>{`> ALLOCATING_VIRTUAL_AGENTS... OK`}</p>
                        <p>{`> CONNECTING_TO_KNOWLEDGE_BASE... [${Math.floor(progress / 10) * 10}ms]`}</p>
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
