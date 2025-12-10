'use client';

import { motion } from 'framer-motion';
import { Github, Heart, ExternalLink } from 'lucide-react';

interface Developer {
    name: string;
    github: string;
}

const developers: Developer[] = [
    {
        name: process.env.NEXT_PUBLIC_DEVELOPER_1_NAME || "Amir Kiarafi",
        github: process.env.NEXT_PUBLIC_DEVELOPER_1_GITHUB || "https://github.com/amirkiarafiei"
    },
    {
        name: process.env.NEXT_PUBLIC_DEVELOPER_2_NAME || "Bora Ilci",
        github: process.env.NEXT_PUBLIC_DEVELOPER_2_GITHUB || "https://github.com/borailci"
    }
];

export default function Footer() {
    const currentYear = new Date().getFullYear();

    return (
        <motion.footer
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.5 }}
            className="relative mt-auto border-t border-[hsl(var(--border))]"
        >
            {/* Gradient line at top */}
            <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-violet-500 to-transparent" />

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                    {/* Left - Copyright */}
                    <div className="flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
                        <span>© {currentYear}</span>
                        <span className="gradient-text font-semibold">Codebase Tutorial Generator</span>
                    </div>

                    {/* Center - Built with love */}
                    <motion.div
                        className="flex items-center gap-2 text-sm"
                        whileHover={{ scale: 1.05 }}
                    >
                        <span className="text-[hsl(var(--muted-foreground))]">Built with</span>
                        <motion.div
                            animate={{ scale: [1, 1.2, 1] }}
                            transition={{ duration: 1, repeat: Infinity }}
                        >
                            <Heart className="w-4 h-4 text-red-500 fill-red-500" />
                        </motion.div>
                        <span className="text-[hsl(var(--muted-foreground))]">by</span>
                        <div className="flex items-center gap-3">
                            {developers.map((dev, index) => (
                                <motion.a
                                    key={dev.name}
                                    href={dev.github}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-1.5 group"
                                    whileHover={{ scale: 1.05 }}
                                    whileTap={{ scale: 0.95 }}
                                >
                                    <Github className="w-4 h-4 text-[hsl(var(--muted-foreground))] group-hover:text-violet-500 transition-colors" />
                                    <span className="font-medium text-[hsl(var(--foreground))] group-hover:text-violet-500 transition-colors">
                                        {dev.name}
                                    </span>
                                    <ExternalLink className="w-3 h-3 text-[hsl(var(--muted-foreground))] opacity-0 group-hover:opacity-100 transition-opacity" />
                                    {index < developers.length - 1 && (
                                        <span className="text-[hsl(var(--muted-foreground))] ml-1">&</span>
                                    )}
                                </motion.a>
                            ))}
                        </div>
                    </motion.div>

                    {/* Right - Tech Stack */}
                    <div className="flex items-center gap-4 text-xs text-[hsl(var(--muted-foreground))]">
                        <motion.a
                            href="https://nextjs.org"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-[hsl(var(--foreground))] transition-colors"
                            whileHover={{ y: -2 }}
                        >
                            Next.js
                        </motion.a>
                        <span>•</span>
                        <motion.a
                            href="https://tailwindcss.com"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-[hsl(var(--foreground))] transition-colors"
                            whileHover={{ y: -2 }}
                        >
                            Tailwind CSS
                        </motion.a>
                        <span>•</span>
                        <motion.a
                            href="https://www.framer.com/motion/"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-[hsl(var(--foreground))] transition-colors"
                            whileHover={{ y: -2 }}
                        >
                            Framer Motion
                        </motion.a>
                    </div>
                </div>
            </div>
        </motion.footer>
    );
}
