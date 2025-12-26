'use client';

import { motion } from 'framer-motion';
import { ScrollArea } from '@/components/ui/scroll-area';
import { FileText, ChevronLeft, ChevronRight, CheckCircle2 } from 'lucide-react';
import { TutorialFile } from '@/types';
import { Button } from '@/components/ui/button';
import { useState, useEffect } from 'react';

interface FileSidebarProps {
    files: TutorialFile[];
    activeFile: string;
    onFileSelect: (path: string) => void;
    accentColor: string;
    codebaseId?: string;
}

export function FileSidebar({ files, activeFile, onFileSelect, accentColor, codebaseId = 'default' }: FileSidebarProps) {
    const [collapsed, setCollapsed] = useState(false);
    const [visitedFiles, setVisitedFiles] = useState<Set<string>>(new Set());

    // Load visited files from localStorage
    useEffect(() => {
        const stored = localStorage.getItem(`visited-${codebaseId}`);
        if (stored) {
            setVisitedFiles(new Set(JSON.parse(stored)));
        }
    }, [codebaseId]);

    // Mark current file as visited
    useEffect(() => {
        if (activeFile && !visitedFiles.has(activeFile)) {
            const newVisited = new Set(visitedFiles);
            newVisited.add(activeFile);
            setVisitedFiles(newVisited);
            localStorage.setItem(`visited-${codebaseId}`, JSON.stringify(Array.from(newVisited)));
        }
    }, [activeFile, codebaseId, visitedFiles]);

    const completedCount = visitedFiles.size;
    const progressPercent = files.length > 0 ? Math.round((completedCount / files.length) * 100) : 0;

    return (
        <motion.aside
            initial={{ x: -20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            className={`relative h-full flex flex-col border-r border-white/10 bg-slate-900/50 transition-all duration-300 ${collapsed ? 'w-12' : 'w-64'
                }`}
        >
            {/* Toggle button */}
            <Button
                variant="ghost"
                size="icon"
                onClick={() => setCollapsed(!collapsed)}
                className="absolute -right-3 top-4 z-10 h-6 w-6 rounded-full border border-white/10 bg-slate-800"
            >
                {collapsed ? (
                    <ChevronRight className="h-3 w-3" />
                ) : (
                    <ChevronLeft className="h-3 w-3" />
                )}
            </Button>

            {!collapsed && (
                <>
                    <div className="border-b border-white/10 p-4">
                        <h3 className="text-sm font-semibold text-slate-300">Modules</h3>
                        {/* Progress bar */}
                        <div className="mt-2 flex items-center gap-2">
                            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-700">
                                <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${progressPercent}%` }}
                                    transition={{ duration: 0.5 }}
                                    className="h-full rounded-full"
                                    style={{ backgroundColor: accentColor }}
                                />
                            </div>
                            <span className="text-xs text-slate-400">{progressPercent}%</span>
                        </div>
                    </div>

                    <ScrollArea className="flex-1">
                        <div className="p-2">
                            {files.map((file, index) => {
                                const isVisited = visitedFiles.has(file.path);
                                const isActive = activeFile === file.path;

                                return (
                                    <motion.button
                                        key={file.path}
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: index * 0.05 }}
                                        onClick={() => onFileSelect(file.path)}
                                        className={`group mb-1 flex w-full items-start gap-3 rounded-lg px-3 py-2 text-left text-sm transition-all ${isActive
                                            ? 'bg-white/10 text-white'
                                            : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                                            }`}
                                        style={{
                                            borderLeft: isActive ? `3px solid ${accentColor}` : '3px solid transparent',
                                        }}
                                    >
                                        {isVisited && !isActive ? (
                                            <CheckCircle2
                                                className="h-4 w-4 flex-shrink-0 mt-0.5 text-green-400"
                                            />
                                        ) : (
                                            <FileText
                                                className="h-4 w-4 flex-shrink-0 mt-0.5"
                                                style={{ color: isActive ? accentColor : undefined }}
                                            />
                                        )}
                                        <span className="break-words">{file.title}</span>
                                    </motion.button>
                                );
                            })}
                        </div>
                    </ScrollArea>
                </>
            )}
        </motion.aside>
    );
}
