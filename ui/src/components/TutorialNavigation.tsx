'use client';

import { motion } from 'framer-motion';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface TutorialNavigationProps {
    files: { path: string; title: string }[];
    activeFile: string;
    onFileSelect: (path: string) => void;
    accentColor?: string;
}

export function TutorialNavigation({ 
    files, 
    activeFile, 
    onFileSelect,
    accentColor = '#8B5CF6'
}: TutorialNavigationProps) {
    const currentIndex = files.findIndex(f => f.path === activeFile);
    const prevFile = currentIndex > 0 ? files[currentIndex - 1] : null;
    const nextFile = currentIndex < files.length - 1 ? files[currentIndex + 1] : null;

    if (files.length <= 1) return null;

    return (
        <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-12 border-t border-slate-700/50 pt-8"
        >
            <div className="flex items-center justify-between gap-4">
                {/* Previous Button */}
                {prevFile ? (
                    <motion.button
                        whileHover={{ scale: 1.02, x: -4 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => onFileSelect(prevFile.path)}
                        className="group flex flex-1 items-center gap-3 rounded-xl border border-slate-700/50 bg-slate-800/50 p-4 text-left transition-all hover:border-slate-600 hover:bg-slate-800"
                    >
                        <div 
                            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-colors"
                            style={{ backgroundColor: `${accentColor}20` }}
                        >
                            <ChevronLeft 
                                className="h-5 w-5 transition-transform group-hover:-translate-x-0.5" 
                                style={{ color: accentColor }}
                            />
                        </div>
                        <div className="min-w-0">
                            <p className="text-xs text-slate-400">Previous</p>
                            <p className="truncate text-sm font-medium text-white">{prevFile.title}</p>
                        </div>
                    </motion.button>
                ) : (
                    <div className="flex-1" />
                )}

                {/* Progress Indicator */}
                <div className="hidden shrink-0 flex-col items-center sm:flex">
                    <span className="text-xs text-slate-500">
                        {currentIndex + 1} of {files.length}
                    </span>
                    <div className="mt-2 flex gap-1">
                        {files.map((_, i) => (
                            <div
                                key={i}
                                className="h-1.5 w-1.5 rounded-full transition-colors"
                                style={{
                                    backgroundColor: i === currentIndex ? accentColor : '#475569'
                                }}
                            />
                        ))}
                    </div>
                </div>

                {/* Next Button */}
                {nextFile ? (
                    <motion.button
                        whileHover={{ scale: 1.02, x: 4 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => onFileSelect(nextFile.path)}
                        className="group flex flex-1 items-center justify-end gap-3 rounded-xl border border-slate-700/50 bg-slate-800/50 p-4 text-right transition-all hover:border-slate-600 hover:bg-slate-800"
                    >
                        <div className="min-w-0">
                            <p className="text-xs text-slate-400">Next</p>
                            <p className="truncate text-sm font-medium text-white">{nextFile.title}</p>
                        </div>
                        <div 
                            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-colors"
                            style={{ backgroundColor: `${accentColor}20` }}
                        >
                            <ChevronRight 
                                className="h-5 w-5 transition-transform group-hover:translate-x-0.5" 
                                style={{ color: accentColor }}
                            />
                        </div>
                    </motion.button>
                ) : (
                    <div className="flex-1" />
                )}
            </div>
        </motion.div>
    );
}
