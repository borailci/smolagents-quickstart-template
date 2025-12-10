'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState, useCallback } from 'react';
import { Sparkles, Brain, Cpu, Zap, Database, Code } from 'lucide-react';

interface LoadingProgressProps {
    isVisible: boolean;
    onComplete: () => void;
    accentColor?: string;
    codebaseName?: string;
}

const loadingMessages = [
    { text: "Initializing AI agents...", icon: Brain },
    { text: "Analyzing codebase structure...", icon: Code },
    { text: "Processing documentation...", icon: Database },
    { text: "Generating tutorial paths...", icon: Cpu },
    { text: "Optimizing content...", icon: Zap },
    { text: "Finalizing tutorial...", icon: Sparkles },
];

// Floating particles component
function FloatingParticles({ color }: { color: string }) {
    return (
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
            {[...Array(20)].map((_, i) => (
                <motion.div
                    key={i}
                    className="absolute w-2 h-2 rounded-full"
                    style={{
                        background: color,
                        left: `${Math.random() * 100}%`,
                        top: `${Math.random() * 100}%`,
                    }}
                    animate={{
                        y: [0, -30, 0],
                        x: [0, Math.random() * 20 - 10, 0],
                        opacity: [0.2, 0.8, 0.2],
                        scale: [0.5, 1, 0.5],
                    }}
                    transition={{
                        duration: 3 + Math.random() * 2,
                        repeat: Infinity,
                        delay: Math.random() * 2,
                        ease: "easeInOut",
                    }}
                />
            ))}
        </div>
    );
}

// Neural network background animation
function NeuralNetwork({ color }: { color: string }) {
    return (
        <svg className="absolute inset-0 w-full h-full opacity-10" viewBox="0 0 800 600">
            {/* Nodes */}
            {[...Array(15)].map((_, i) => {
                const x = 100 + Math.random() * 600;
                const y = 100 + Math.random() * 400;
                return (
                    <motion.circle
                        key={i}
                        cx={x}
                        cy={y}
                        r="4"
                        fill={color}
                        animate={{
                            opacity: [0.3, 1, 0.3],
                            scale: [1, 1.5, 1],
                        }}
                        transition={{
                            duration: 2 + Math.random(),
                            repeat: Infinity,
                            delay: Math.random() * 2,
                        }}
                    />
                );
            })}
            {/* Connections */}
            {[...Array(20)].map((_, i) => {
                const x1 = 100 + Math.random() * 600;
                const y1 = 100 + Math.random() * 400;
                const x2 = 100 + Math.random() * 600;
                const y2 = 100 + Math.random() * 400;
                return (
                    <motion.line
                        key={`line-${i}`}
                        x1={x1}
                        y1={y1}
                        x2={x2}
                        y2={y2}
                        stroke={color}
                        strokeWidth="1"
                        initial={{ pathLength: 0, opacity: 0 }}
                        animate={{
                            pathLength: [0, 1, 0],
                            opacity: [0, 0.3, 0],
                        }}
                        transition={{
                            duration: 3,
                            repeat: Infinity,
                            delay: i * 0.2,
                            ease: "easeInOut",
                        }}
                    />
                );
            })}
        </svg>
    );
}

export default function LoadingProgress({
    isVisible,
    onComplete,
    accentColor = '#8B5CF6',
    codebaseName = 'Tutorial'
}: LoadingProgressProps) {
    const [progress, setProgress] = useState(0);
    const [messageIndex, setMessageIndex] = useState(0);

    const loadingDuration = parseInt(process.env.NEXT_PUBLIC_LOADING_DURATION_MS || '3500');

    const completeLoading = useCallback(() => {
        onComplete();
    }, [onComplete]);

    useEffect(() => {
        if (!isVisible) {
            setProgress(0);
            setMessageIndex(0);
            return;
        }

        const progressInterval = setInterval(() => {
            setProgress(prev => {
                const next = prev + (100 / (loadingDuration / 50));
                if (next >= 100) {
                    clearInterval(progressInterval);
                    setTimeout(completeLoading, 300);
                    return 100;
                }
                return next;
            });
        }, 50);

        const messageInterval = setInterval(() => {
            setMessageIndex(prev => (prev + 1) % loadingMessages.length);
        }, loadingDuration / (loadingMessages.length + 1));

        return () => {
            clearInterval(progressInterval);
            clearInterval(messageInterval);
        };
    }, [isVisible, loadingDuration, completeLoading]);

    const CurrentIcon = loadingMessages[messageIndex].icon;

    return (
        <AnimatePresence>
            {isVisible && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.5 }}
                    className="fixed inset-0 z-50 flex items-center justify-center"
                    style={{
                        background: `radial-gradient(ellipse at center, hsl(var(--background)) 0%, hsl(222.2 84% 2%) 100%)`
                    }}
                >
                    {/* Background effects */}
                    <NeuralNetwork color={accentColor} />
                    <FloatingParticles color={accentColor} />

                    {/* Radial glow */}
                    <div
                        className="absolute w-96 h-96 rounded-full blur-3xl opacity-20"
                        style={{ background: accentColor }}
                    />

                    {/* Content */}
                    <div className="relative z-10 flex flex-col items-center max-w-md mx-auto px-4">
                        {/* Title */}
                        <motion.h2
                            initial={{ opacity: 0, y: -20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="text-2xl md:text-3xl font-bold text-center mb-8"
                        >
                            Loading{' '}
                            <span style={{ color: accentColor }}>{codebaseName}</span>
                        </motion.h2>

                        {/* Progress Ring */}
                        <div className="relative mb-8">
                            <svg className="w-48 h-48 transform -rotate-90">
                                {/* Background circle */}
                                <circle
                                    cx="96"
                                    cy="96"
                                    r="88"
                                    fill="none"
                                    stroke="hsl(var(--secondary))"
                                    strokeWidth="8"
                                />
                                {/* Progress circle */}
                                <motion.circle
                                    cx="96"
                                    cy="96"
                                    r="88"
                                    fill="none"
                                    stroke={accentColor}
                                    strokeWidth="8"
                                    strokeLinecap="round"
                                    strokeDasharray={553}
                                    strokeDashoffset={553 - (553 * progress) / 100}
                                    style={{
                                        filter: `drop-shadow(0 0 10px ${accentColor})`,
                                    }}
                                />
                            </svg>

                            {/* Center content */}
                            <div className="absolute inset-0 flex flex-col items-center justify-center">
                                <motion.div
                                    animate={{
                                        rotate: 360,
                                        scale: [1, 1.1, 1],
                                    }}
                                    transition={{
                                        rotate: { duration: 3, repeat: Infinity, ease: "linear" },
                                        scale: { duration: 1.5, repeat: Infinity, ease: "easeInOut" }
                                    }}
                                    className="mb-2"
                                >
                                    <CurrentIcon
                                        className="w-10 h-10"
                                        style={{ color: accentColor }}
                                    />
                                </motion.div>
                                <motion.span
                                    key={progress}
                                    initial={{ scale: 1.2, opacity: 0 }}
                                    animate={{ scale: 1, opacity: 1 }}
                                    className="text-4xl font-bold"
                                    style={{ color: accentColor }}
                                >
                                    {Math.round(progress)}%
                                </motion.span>
                            </div>
                        </div>

                        {/* Loading message */}
                        <motion.div
                            key={messageIndex}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="flex items-center gap-3 text-lg text-[hsl(var(--muted-foreground))]"
                        >
                            <motion.div
                                animate={{
                                    rotate: [0, 360],
                                }}
                                transition={{
                                    duration: 2,
                                    repeat: Infinity,
                                    ease: "linear"
                                }}
                            >
                                <CurrentIcon className="w-5 h-5" style={{ color: accentColor }} />
                            </motion.div>
                            <span>{loadingMessages[messageIndex].text}</span>
                        </motion.div>

                        {/* Progress bar */}
                        <div className="w-full mt-8">
                            <div className="h-2 bg-[hsl(var(--secondary))] rounded-full overflow-hidden">
                                <motion.div
                                    className="h-full rounded-full"
                                    style={{
                                        background: `linear-gradient(90deg, ${accentColor}, ${accentColor}80)`,
                                        boxShadow: `0 0 20px ${accentColor}`,
                                    }}
                                    initial={{ width: 0 }}
                                    animate={{ width: `${progress}%` }}
                                    transition={{ duration: 0.1 }}
                                />
                            </div>
                        </div>

                        {/* Decorative text */}
                        <motion.p
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 0.5 }}
                            transition={{ delay: 1 }}
                            className="text-xs text-[hsl(var(--muted-foreground))] mt-6 text-center"
                        >
                            AI-powered tutorial generation in progress...
                        </motion.p>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
