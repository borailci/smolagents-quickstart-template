"use client";

import { Github } from 'lucide-react';

export default function Footer() {
    const dev1 = process.env.NEXT_PUBLIC_DEVELOPER_1_NAME || 'Developer 1';
    const dev1Url = process.env.NEXT_PUBLIC_DEVELOPER_1_GITHUB || '#';
    const dev2 = process.env.NEXT_PUBLIC_DEVELOPER_2_NAME || 'Developer 2';
    const dev2Url = process.env.NEXT_PUBLIC_DEVELOPER_2_GITHUB || '#';
    const repoUrl = process.env.NEXT_PUBLIC_REPO_URL || '#';

    return (
        <footer className="mt-auto py-8 border-t border-white/5 bg-black/20 backdrop-blur-sm">
            <div className="container mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-gray-400">
                <div className="flex items-center gap-1">
                    Built by
                    <a href={dev1Url} target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:text-cyan-300 transition-colors">
                        {dev1}
                    </a>
                    &
                    <a href={dev2Url} target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:text-purple-300 transition-colors">
                        {dev2}
                    </a>
                </div>

                <div className="flex items-center gap-4">
                    <span>&copy; {new Date().getFullYear()} Codebase Tutorial Generator</span>
                    <a href={repoUrl} target="_blank" rel="noopener noreferrer" className="p-2 hover:bg-white/10 rounded-full transition-colors" aria-label="GitHub Repository">
                        <Github className="w-5 h-5" />
                    </a>
                </div>
            </div>
        </footer>
    );
}
