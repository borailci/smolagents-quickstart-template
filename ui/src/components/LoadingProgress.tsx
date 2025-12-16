'use client';

import { motion } from 'framer-motion';
import { Sparkles, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';

interface LoadingProgressProps {
    accentColor: string;
    onComplete: () => void;
}

const messages = [
    'Processing codebase...',
    'Analyzing structure...',
    'Generating tutorial...',
    'Preparing content...',
];

const duration = parseInt(process.env.NEXT_PUBLIC_LOADING_DURATION_MS || '3500', 10);

export function LoadingProgress({ accentColor, onComplete }: LoadingProgressProps) {
    const [progress, setProgress] = useState(0);
    const [messageIndex, setMessageIndex] = useState(0);

    useEffect(() => {
        const startTime = Date.now();
        const interval = setInterval(() => {
            const elapsed = Date.now() - startTime;
            const newProgress = Math.min((elapsed / duration) * 100, 100);
            setProgress(newProgress);

            // Cycle messages
            const msgIdx = Math.floor((elapsed / duration) * messages.length) % messages.length;
            setMessageIndex(msgIdx);

            if (newProgress >= 100) {
                clearInterval(interval);
                setTimeout(onComplete, 300);
            }
        }, 16);

        return () => clearInterval(interval);
    }, [onComplete]);

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/95 backdrop-blur-xl"
        >
            {/* Animated background particles */}
            <div className="absolute inset-0 overflow-hidden">
                {[...Array(20)].map((_, i) => (
                    <motion.div
                        key={i}
                        className="absolute h-2 w-2 rounded-full"
                        style={{ backgroundColor: `${accentColor}40` }}
                        initial={{
                            x: Math.random() * (typeof window !== 'undefined' ? window.innerWidth : 1000),
                            y: Math.random() * (typeof window !== 'undefined' ? window.innerHeight : 800),
                        }}
                        animate={{
                            y: [null, -100],
                            opacity: [0.5, 0],
                        }}
                        transition={{
                            duration: 2 + Math.random() * 2,
                            repeat: Infinity,
                            delay: Math.random() * 2,
                        }}
                    />
                ))}
            </div>

            <div className="relative flex flex-col items-center gap-8">
                {/* Spinning loader icon */}
                <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                >
                    <div
                        className="flex h-24 w-24 items-center justify-center rounded-full"
                        style={{ backgroundColor: `${accentColor}20` }}
                    >
                        <Sparkles className="h-12 w-12" style={{ color: accentColor }} />
                    </div>
                </motion.div>

                {/* Progress ring */}
                <div className="relative h-32 w-32">
                    <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100">
                        {/* Background ring */}
                        <circle
                            cx="50"
                            cy="50"
                            r="45"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="4"
                            className="text-slate-700"
                        />
                        {/* Progress ring */}
                        <motion.circle
                            cx="50"
                            cy="50"
                            r="45"
                            fill="none"
                            stroke={accentColor}
                            strokeWidth="4"
                            strokeLinecap="round"
                            strokeDasharray={283}
                            strokeDashoffset={283 - (283 * progress) / 100}
                            style={{ filter: `drop-shadow(0 0 8px ${accentColor})` }}
                        />
                    </svg>
                    {/* Percentage */}
                    <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-2xl font-bold text-white">{Math.round(progress)}%</span>
                    </div>
                </div>

                {/* Message */}
                <motion.div
                    key={messageIndex}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center gap-3"
                >
                    <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                    <span className="text-lg text-slate-300">{messages[messageIndex]}</span>
                </motion.div>
            </div>
        </motion.div>
    );
}
