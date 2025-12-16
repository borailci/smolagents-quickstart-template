'use client';

import { Github, Heart } from 'lucide-react';
import { motion } from 'framer-motion';

const dev1Name = process.env.NEXT_PUBLIC_DEVELOPER_1_NAME || 'Developer 1';
const dev1Github = process.env.NEXT_PUBLIC_DEVELOPER_1_GITHUB || '#';
const dev2Name = process.env.NEXT_PUBLIC_DEVELOPER_2_NAME || 'Developer 2';
const dev2Github = process.env.NEXT_PUBLIC_DEVELOPER_2_GITHUB || '#';
const repoUrl = process.env.NEXT_PUBLIC_REPO_URL || '#';

export function Footer() {
    return (
        <motion.footer
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="border-t border-white/10 bg-slate-900/50 py-6"
        >
            <div className="container mx-auto flex flex-col items-center gap-4 px-6 md:flex-row md:justify-between">
                <div className="flex items-center gap-2 text-sm text-slate-400">
                    <span>Built with</span>
                    <Heart className="h-4 w-4 text-rose-400" />
                    <span>by</span>
                    <motion.a
                        href={dev1Github}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-violet-400 hover:text-violet-300"
                        whileHover={{ scale: 1.05 }}
                    >
                        {dev1Name}
                    </motion.a>
                    <span>&</span>
                    <motion.a
                        href={dev2Github}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-cyan-400 hover:text-cyan-300"
                        whileHover={{ scale: 1.05 }}
                    >
                        {dev2Name}
                    </motion.a>
                </div>

                <motion.a
                    href={repoUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-slate-400 hover:text-white"
                    whileHover={{ scale: 1.05 }}
                >
                    <Github className="h-5 w-5" />
                    <span className="text-sm">View on GitHub</span>
                </motion.a>
            </div>
        </motion.footer>
    );
}
