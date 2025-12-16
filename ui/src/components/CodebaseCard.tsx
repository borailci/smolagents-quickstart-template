'use client';

import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Codebase } from '@/types';
import { Code, Bot, FileCode, Folder, Cpu, Database, Globe, Server } from 'lucide-react';

// Static icon map for common icons
const iconMap: Record<string, React.ComponentType<{ className?: string; style?: React.CSSProperties }>> = {
    robot: Bot,
    code: Code,
    filecode: FileCode,
    folder: Folder,
    cpu: Cpu,
    database: Database,
    globe: Globe,
    server: Server,
};

interface CodebaseCardProps {
    codebase: Codebase;
    index: number;
    onClick: () => void;
}

export function CodebaseCard({ codebase, index, onClick }: CodebaseCardProps) {
    const IconComponent = iconMap[codebase.icon.toLowerCase()] || Code;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1, duration: 0.4 }}
            whileHover={{ scale: 1.02, y: -5 }}
            whileTap={{ scale: 0.98 }}
            onClick={onClick}
            className="cursor-pointer"
        >
            <Card className="group relative overflow-hidden border-white/10 bg-gradient-to-br from-slate-800/80 to-slate-900/80 backdrop-blur-xl transition-all duration-300 hover:border-white/20 hover:shadow-2xl hover:shadow-violet-500/10">
                {/* Glow effect */}
                <div
                    className="absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
                    style={{
                        background: `radial-gradient(circle at 50% 0%, ${codebase.color}20, transparent 50%)`,
                    }}
                />

                <CardHeader className="relative">
                    <div className="flex items-center gap-4">
                        <div
                            className="flex h-12 w-12 items-center justify-center rounded-xl"
                            style={{ backgroundColor: `${codebase.color}20` }}
                        >
                            <IconComponent
                                className="h-6 w-6"
                                style={{ color: codebase.color }}
                            />
                        </div>
                        <div>
                            <CardTitle className="text-lg text-white">{codebase.name}</CardTitle>
                            <CardDescription className="text-slate-400">
                                {codebase.files.length} modules
                            </CardDescription>
                        </div>
                    </div>
                </CardHeader>

                <CardContent className="relative">
                    <p className="text-sm text-slate-300">{codebase.description}</p>

                    {/* File preview tags */}
                    <div className="mt-4 flex flex-wrap gap-2">
                        {codebase.files.slice(0, 3).map((file, i) => (
                            <span
                                key={i}
                                className="rounded-full bg-slate-700/50 px-3 py-1 text-xs text-slate-300"
                            >
                                {file.title.replace('Module ', '').split(':')[0]}
                            </span>
                        ))}
                        {codebase.files.length > 3 && (
                            <span className="rounded-full bg-slate-700/50 px-3 py-1 text-xs text-slate-400">
                                +{codebase.files.length - 3} more
                            </span>
                        )}
                    </div>
                </CardContent>

                {/* Bottom gradient accent */}
                <div
                    className="absolute bottom-0 left-0 right-0 h-1 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
                    style={{ background: `linear-gradient(90deg, ${codebase.color}, ${codebase.color}80)` }}
                />
            </Card>
        </motion.div>
    );
}
