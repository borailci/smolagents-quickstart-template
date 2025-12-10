'use client';

import { motion } from 'framer-motion';
import {
    Bot, Link, Cpu, Flame, Database, Code,
    Sparkles, FileText, Clock, ArrowRight
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Codebase } from '@/types';

const iconMap: { [key: string]: React.ComponentType<{ className?: string }> } = {
    Bot,
    Link,
    Cpu,
    Flame,
    Database,
    Code,
    Sparkles,
};

interface CodebaseCardProps {
    codebase: Codebase;
    index: number;
}

export default function CodebaseCard({ codebase, index }: CodebaseCardProps) {
    const router = useRouter();
    const Icon = iconMap[codebase.icon] || Code;

    const handleClick = () => {
        router.push(`/tutorial/${codebase.id}`);
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
                duration: 0.5,
                delay: index * 0.1,
                ease: "easeOut"
            }}
            whileHover={{
                y: -8,
                transition: { duration: 0.2 }
            }}
            onClick={handleClick}
            className="group cursor-pointer relative"
        >
            {/* Glow effect behind card */}
            <div
                className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-xl"
                style={{
                    background: `linear-gradient(135deg, ${codebase.color}40, transparent)`
                }}
            />

            {/* Card */}
            <div className="relative glass-card rounded-2xl p-6 h-full overflow-hidden transition-all duration-300 group-hover:border-[hsl(var(--primary)/0.5)]">
                {/* Animated gradient border on hover */}
                <div className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                    <div className="absolute inset-0 rounded-2xl animated-gradient opacity-20" />
                </div>

                {/* Content */}
                <div className="relative z-10">
                    {/* Icon & Badge */}
                    <div className="flex items-start justify-between mb-4">
                        <motion.div
                            whileHover={{ rotate: 15, scale: 1.1 }}
                            className="w-14 h-14 rounded-xl flex items-center justify-center relative"
                            style={{
                                background: `linear-gradient(135deg, ${codebase.color}30, ${codebase.color}10)`
                            }}
                        >
                            <Icon
                                className="w-7 h-7"
                                style={{ color: codebase.color }}
                            />
                            {/* Icon glow */}
                            <div
                                className="absolute inset-0 rounded-xl blur-lg opacity-50"
                                style={{ background: codebase.color }}
                            />
                        </motion.div>

                        <motion.div
                            className="flex items-center gap-1 text-xs font-medium px-3 py-1 rounded-full"
                            style={{
                                background: `${codebase.color}20`,
                                color: codebase.color
                            }}
                            whileHover={{ scale: 1.05 }}
                        >
                            <FileText className="w-3 h-3" />
                            <span>{codebase.files.length} modules</span>
                        </motion.div>
                    </div>

                    {/* Title */}
                    <h3 className="text-xl font-bold mb-2 group-hover:text-[hsl(var(--primary))] transition-colors">
                        {codebase.name}
                    </h3>

                    {/* Description */}
                    <p className="text-sm text-[hsl(var(--muted-foreground))] mb-4 line-clamp-2">
                        {codebase.description}
                    </p>

                    {/* Footer */}
                    <div className="flex items-center justify-between pt-4 border-t border-[hsl(var(--border)/0.5)]">
                        <div className="flex items-center gap-1.5 text-xs text-[hsl(var(--muted-foreground))]">
                            <Clock className="w-3.5 h-3.5" />
                            <span>{Math.ceil(codebase.files.length * 8)} min read</span>
                        </div>

                        <motion.div
                            className="flex items-center gap-1 text-sm font-medium"
                            style={{ color: codebase.color }}
                            whileHover={{ x: 5 }}
                        >
                            <span>Explore</span>
                            <ArrowRight className="w-4 h-4" />
                        </motion.div>
                    </div>
                </div>

                {/* Decorative elements */}
                <div
                    className="absolute top-0 right-0 w-32 h-32 rounded-full blur-3xl opacity-10 group-hover:opacity-20 transition-opacity"
                    style={{ background: codebase.color }}
                />
                <div
                    className="absolute bottom-0 left-0 w-24 h-24 rounded-full blur-3xl opacity-5 group-hover:opacity-15 transition-opacity"
                    style={{ background: codebase.color }}
                />
            </div>
        </motion.div>
    );
}
