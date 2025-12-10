'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { FileText, ChevronLeft, Menu, X } from 'lucide-react';
import { useState } from 'react';
import { TutorialFile } from '@/types';
import { cn } from '@/lib/utils';

interface FileSidebarProps {
    files: TutorialFile[];
    activeFile: string;
    onFileSelect: (path: string) => void;
    accentColor?: string;
}

export default function FileSidebar({
    files,
    activeFile,
    onFileSelect,
    accentColor = '#8B5CF6'
}: FileSidebarProps) {
    const [isCollapsed, setIsCollapsed] = useState(false);
    const [isMobileOpen, setIsMobileOpen] = useState(false);

    const sidebarContent = (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-[hsl(var(--border))]">
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wider">
                        Tutorial Files
                    </h3>
                    <motion.button
                        onClick={() => setIsCollapsed(!isCollapsed)}
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.95 }}
                        className="p-1.5 rounded-lg hover:bg-[hsl(var(--secondary))] transition-colors hidden md:block"
                    >
                        <ChevronLeft className={cn(
                            "w-4 h-4 transition-transform duration-300",
                            isCollapsed && "rotate-180"
                        )} />
                    </motion.button>
                    <motion.button
                        onClick={() => setIsMobileOpen(false)}
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.95 }}
                        className="p-1.5 rounded-lg hover:bg-[hsl(var(--secondary))] transition-colors md:hidden"
                    >
                        <X className="w-4 h-4" />
                    </motion.button>
                </div>
            </div>

            {/* File List */}
            <div className="flex-1 overflow-y-auto p-2">
                <AnimatePresence>
                    {files.map((file, index) => (
                        <motion.button
                            key={file.path}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.05 }}
                            onClick={() => {
                                onFileSelect(file.path);
                                setIsMobileOpen(false);
                            }}
                            className={cn(
                                "w-full text-left px-3 py-3 rounded-xl mb-1 transition-all duration-200 group relative overflow-hidden",
                                activeFile === file.path
                                    ? "bg-[hsl(var(--primary)/0.15)]"
                                    : "hover:bg-[hsl(var(--secondary)/0.5)]"
                            )}
                        >
                            {/* Active indicator */}
                            {activeFile === file.path && (
                                <motion.div
                                    layoutId="activeFile"
                                    className="absolute left-0 top-0 bottom-0 w-1 rounded-r-full"
                                    style={{ background: accentColor }}
                                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                                />
                            )}

                            <div className="flex items-start gap-3">
                                <div
                                    className={cn(
                                        "mt-0.5 p-1.5 rounded-lg transition-colors",
                                        activeFile === file.path
                                            ? "bg-[hsl(var(--primary)/0.2)]"
                                            : "bg-[hsl(var(--secondary))] group-hover:bg-[hsl(var(--primary)/0.1)]"
                                    )}
                                >
                                    <FileText
                                        className={cn(
                                            "w-4 h-4 transition-colors",
                                            activeFile === file.path
                                                ? "text-[hsl(var(--primary))]"
                                                : "text-[hsl(var(--muted-foreground))] group-hover:text-[hsl(var(--primary))]"
                                        )}
                                        style={activeFile === file.path ? { color: accentColor } : undefined}
                                    />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className={cn(
                                        "text-sm font-medium truncate transition-colors",
                                        activeFile === file.path
                                            ? "text-[hsl(var(--foreground))]"
                                            : "text-[hsl(var(--muted-foreground))] group-hover:text-[hsl(var(--foreground))]"
                                    )}>
                                        {file.title}
                                    </p>
                                    <p className="text-xs text-[hsl(var(--muted-foreground))] truncate mt-0.5 opacity-60">
                                        {file.path.split('/').pop()}
                                    </p>
                                </div>
                            </div>

                            {/* Hover glow */}
                            <div
                                className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity rounded-xl"
                                style={{ background: accentColor }}
                            />
                        </motion.button>
                    ))}
                </AnimatePresence>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-[hsl(var(--border))]">
                <div className="text-xs text-[hsl(var(--muted-foreground))] text-center">
                    {files.length} files in tutorial
                </div>
            </div>
        </div>
    );

    return (
        <>
            {/* Mobile trigger */}
            <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsMobileOpen(true)}
                className="md:hidden fixed bottom-4 left-4 z-40 p-3 rounded-xl glass glow-hover"
                style={{ boxShadow: `0 0 20px ${accentColor}40` }}
            >
                <Menu className="w-5 h-5" />
            </motion.button>

            {/* Mobile overlay */}
            <AnimatePresence>
                {isMobileOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setIsMobileOpen(false)}
                        className="md:hidden fixed inset-0 bg-black/50 z-40"
                    />
                )}
            </AnimatePresence>

            {/* Sidebar */}
            <motion.aside
                initial={{ x: -300 }}
                animate={{
                    x: 0,
                    width: isCollapsed ? 60 : 280
                }}
                transition={{ duration: 0.3 }}
                className={cn(
                    "fixed md:sticky top-16 left-0 h-[calc(100vh-4rem)] z-40",
                    "glass border-r border-[hsl(var(--border))]",
                    "md:translate-x-0",
                    isMobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
                )}
                style={{ width: isCollapsed ? 60 : 280 }}
            >
                {!isCollapsed ? (
                    sidebarContent
                ) : (
                    // Collapsed view
                    <div className="h-full flex flex-col items-center py-4 gap-2">
                        <motion.button
                            onClick={() => setIsCollapsed(false)}
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.95 }}
                            className="p-2 rounded-lg hover:bg-[hsl(var(--secondary))] transition-colors mb-4"
                        >
                            <ChevronLeft className="w-4 h-4 rotate-180" />
                        </motion.button>
                        {files.map((file, index) => (
                            <motion.button
                                key={file.path}
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: index * 0.05 }}
                                onClick={() => onFileSelect(file.path)}
                                className={cn(
                                    "p-2 rounded-lg transition-all",
                                    activeFile === file.path
                                        ? "bg-[hsl(var(--primary)/0.2)]"
                                        : "hover:bg-[hsl(var(--secondary))]"
                                )}
                                title={file.title}
                            >
                                <FileText
                                    className="w-4 h-4"
                                    style={activeFile === file.path ? { color: accentColor } : undefined}
                                />
                            </motion.button>
                        ))}
                    </div>
                )}
            </motion.aside>
        </>
    );
}
