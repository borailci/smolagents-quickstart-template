"use client";

import Link from 'next/link';
import { Sparkles, Github } from 'lucide-react';

export default function Header() {
    return (
        <header className="fixed top-0 left-0 right-0 z-50 h-16 glass-panel border-b border-white/5">
            <div className="container mx-auto h-full flex items-center justify-between px-4">
                <Link href="/" className="flex items-center gap-2 group">
                    <div className="p-2 bg-gradient-to-br from-purple-600 to-cyan-500 rounded-lg group-hover:scale-110 transition-transform">
                        <Sparkles className="w-5 h-5 text-white" />
                    </div>
                    <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                        Codebase Tutorial Generator
                    </span>
                </Link>

                {/* Placeholder for future nav items or theme toggle */}
            </div>
        </header>
    );
}
