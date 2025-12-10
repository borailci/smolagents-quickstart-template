"use client";

import { CodebaseConfig } from "@/types";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FileText, FolderOpen, ChevronLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

interface FileSidebarProps {
    codebase: CodebaseConfig;
}

export function FileSidebar({ codebase }: FileSidebarProps) {
    const searchParams = useSearchParams();
    const currentPath = searchParams.get("file") || codebase.files[0]?.path;

    return (
        <div className="w-80 h-[calc(100vh-4rem)] fixed top-16 left-0 border-r border-white/5 bg-background/50 backdrop-blur-md overflow-y-auto custom-scrollbar">
            <div className="p-4">
                <Link
                    href="/"
                    className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors mb-6 group"
                >
                    <ChevronLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                    Back to Projects
                </Link>

                {/* Header */}
                <div className="flex items-center gap-3 mb-6 p-3 rounded-lg bg-white/5 border border-white/5">
                    <div className="p-2 rounded bg-background">
                        {/* We map icon name to component elsewhere, reusing placeholder here or just generic */}
                        <FolderOpen className="w-5 h-5" style={{ color: codebase.color }} />
                    </div>
                    <div>
                        <h2 className="font-bold text-sm text-white">{codebase.name}</h2>
                        <p className="text-xs text-gray-500">{codebase.files.length} files</p>
                    </div>
                </div>

                <div className="space-y-1">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-600 mb-3 px-2">
                        Tutorial Modules
                    </h3>
                    {codebase.files.map((file, idx) => {
                        const isActive = currentPath === file.path;
                        return (
                            <Link
                                key={file.path}
                                href={`?file=${encodeURIComponent(file.path)}`}
                                className={cn(
                                    "group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all relative overflow-hidden",
                                    isActive
                                        ? "bg-primary/10 text-primary font-medium"
                                        : "text-gray-400 hover:bg-white/5 hover:text-gray-200"
                                )}
                            >
                                {isActive && (
                                    <motion.div
                                        layoutId="activeFile"
                                        className="absolute inset-0 bg-primary/10 border-l-2 border-primary"
                                        initial={false}
                                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                                    />
                                )}
                                <FileText className={cn("w-4 h-4 z-10", isActive ? "text-primary" : "text-gray-500")} />
                                <span className="z-10 truncate relative">{file.title || file.path}</span>
                            </Link>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
