'use client';

import { Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

export function Header() {
    return (
        <motion.header
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="fixed top-0 left-0 right-0 z-50 border-b border-white/10 bg-slate-900/80 backdrop-blur-xl"
        >
            <div className="container mx-auto flex h-16 items-center justify-between px-6">
                <motion.div
                    className="flex items-center gap-3"
                    whileHover={{ scale: 1.02 }}
                >
                    <Sparkles className="h-6 w-6 text-violet-400" />
                    <h1 className="bg-gradient-to-r from-violet-400 via-cyan-400 to-violet-400 bg-clip-text text-xl font-bold text-transparent">
                        Codebase Tutorial Generator
                    </h1>
                </motion.div>
            </div>
        </motion.header>
    );
}
