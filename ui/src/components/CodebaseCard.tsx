"use client";

import { motion } from "framer-motion";
import {
    BotMessageSquare,
    Server,
    BrainCircuit,
    Network,
    Webhook,
    Code,
    FileText,
    Clock
} from "lucide-react";
import Link from "next/link";
import { CodebaseConfig } from "@/types";
import { useState } from "react";
import { LoadingProgress } from "./LoadingProgress";
import { useRouter } from "next/navigation";

const IconMap: Record<string, any> = {
    "bot-message-square": BotMessageSquare,
    "server": Server,
    "brain-circuit": BrainCircuit,
    "network": Network,
    "webhook": Webhook,
    "code": Code,
};

interface CodebaseCardProps {
    codebase: CodebaseConfig;
}

export function CodebaseCard({ codebase }: CodebaseCardProps) {
    const Icon = IconMap[codebase.icon] || Code;
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);

    const handleClick = (e: React.MouseEvent) => {
        e.preventDefault();
        setIsLoading(true);
    };

    const handleLoadingComplete = () => {
        // Navigate to the first file of the tutorial
        const firstFile = codebase.files[0];
        if (firstFile) {
            // We use the codebase ID in the URL, the tutorial page will load the list
            router.push(`/tutorial/${codebase.id}`);
        } else {
            setIsLoading(false);
        }
    };

    return (
        <>
            {isLoading && (
                <LoadingProgress
                    message="Initializing Agent..."
                    onComplete={handleLoadingComplete}
                    accentColor={codebase.color}
                />
            )}
            <Link href={`/tutorial/${codebase.id}`} onClick={handleClick} className="block h-full">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    whileHover={{ scale: 1.02, translateY: -4 }}
                    transition={{ duration: 0.15, ease: "easeOut" }}
                    className="group relative h-full glass-panel rounded-xl overflow-hidden p-6 transition-all duration-150 hover:shadow-2xl hover:shadow-purple-500/20 hover:border-purple-500/30"
                    style={{
                        boxShadow: `0 0 0 1px ${codebase.color}20`,
                    }}
                >
                    <div
                        className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-500"
                        style={{ background: `linear-gradient(135deg, ${codebase.color}, transparent)` }}
                    />

                    <div className="relative z-10 flex flex-col h-full gap-4">
                        <div className="flex items-start justify-between">
                            <div
                                className="p-3 rounded-xl bg-white/5 border border-white/10 group-hover:bg-white/10 transition-colors"
                                style={{ color: codebase.color }}
                            >
                                <Icon className="w-8 h-8" />
                            </div>
                            <div className="px-2 py-1 rounded-full bg-white/5 text-xs text-gray-400 font-mono border border-white/5">
                                {codebase.id}
                            </div>
                        </div>

                        <div>
                            <h3 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-200 mb-2">
                                {codebase.name}
                            </h3>
                            <p className="text-sm text-gray-400 leading-relaxed">
                                {codebase.description}
                            </p>
                        </div>

                        <div className="mt-auto pt-4 flex items-center gap-4 text-xs text-gray-500 border-t border-white/5">
                            <div className="flex items-center gap-1.5">
                                <FileText className="w-4 h-4" />
                                <span>{codebase.files.length} Modules</span>
                            </div>
                            {/* Simulated reading time */}
                            <div className="flex items-center gap-1.5">
                                <Clock className="w-4 h-4" />
                                <span>~{codebase.files.length * 5} min</span>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </Link>
        </>
    );
}
