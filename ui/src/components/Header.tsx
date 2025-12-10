'use client';

import { motion } from 'framer-motion';
import { Sparkles, Moon, Sun, Github } from 'lucide-react';
import Link from 'next/link';
import { useTheme } from '@/hooks/useTheme';

export default function Header() {
    const { theme, toggleTheme } = useTheme();

    return (
        <motion.header
            initial={{ y: -100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="fixed top-0 left-0 right-0 z-50 glass"
        >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-3 group">
                        <motion.div
                            whileHover={{ rotate: 180, scale: 1.1 }}
                            transition={{ duration: 0.5 }}
                            className="relative"
                        >
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center">
                                <Sparkles className="w-5 h-5 text-white" />
                            </div>
                            <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-violet-500 to-cyan-500 blur-lg opacity-50 group-hover:opacity-75 transition-opacity" />
                        </motion.div>
                        <div className="flex flex-col">
                            <motion.span
                                className="text-lg font-bold gradient-text"
                                whileHover={{ scale: 1.02 }}
                            >
                                Codebase Tutorial Generator
                            </motion.span>
                            <span className="text-xs text-[hsl(var(--muted-foreground))] hidden sm:block">
                                AI-Powered Learning Paths
                            </span>
                        </div>
                    </Link>

                    {/* Right Section */}
                    <div className="flex items-center gap-4">
                        {/* GitHub Link */}
                        <motion.a
                            href="https://github.com/amirkiarafiei/codebase-tutorial-generator"
                            target="_blank"
                            rel="noopener noreferrer"
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.95 }}
                            className="p-2 rounded-lg hover:bg-[hsl(var(--secondary))] transition-colors"
                        >
                            <Github className="w-5 h-5" />
                        </motion.a>

                        {/* Theme Toggle */}
                        <motion.button
                            onClick={toggleTheme}
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.95 }}
                            className="p-2 rounded-lg hover:bg-[hsl(var(--secondary))] transition-colors relative overflow-hidden"
                        >
                            <motion.div
                                initial={false}
                                animate={{
                                    rotate: theme === 'dark' ? 0 : 180,
                                    opacity: 1
                                }}
                                transition={{ duration: 0.3 }}
                            >
                                {theme === 'dark' ? (
                                    <Moon className="w-5 h-5" />
                                ) : (
                                    <Sun className="w-5 h-5" />
                                )}
                            </motion.div>
                        </motion.button>
                    </div>
                </div>
            </div>
        </motion.header>
    );
}
