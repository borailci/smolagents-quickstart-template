'use client';

import { motion } from 'framer-motion';
import {
    ArrowLeft, Eye, Edit3, ZoomIn, ZoomOut,
    Maximize2, Moon, Sun, Home
} from 'lucide-react';
import Link from 'next/link';
import { useTheme } from '@/hooks/useTheme';

interface ToolbarProps {
    codebaseName: string;
    currentFileName: string;
    isEditMode: boolean;
    onToggleEditMode: () => void;
    onZoomIn?: () => void;
    onZoomOut?: () => void;
    onFullscreen?: () => void;
    accentColor?: string;
}

export default function Toolbar({
    codebaseName,
    currentFileName,
    isEditMode,
    onToggleEditMode,
    onZoomIn,
    onZoomOut,
    onFullscreen,
    accentColor = '#8B5CF6'
}: ToolbarProps) {
    const { theme, toggleTheme } = useTheme();

    return (
        <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="sticky top-16 z-30 glass border-b border-[hsl(var(--border))]"
        >
            <div className="flex items-center justify-between px-4 py-3">
                {/* Left section - Navigation */}
                <div className="flex items-center gap-4">
                    {/* Back button */}
                    <Link href="/">
                        <motion.button
                            whileHover={{ scale: 1.05, x: -2 }}
                            whileTap={{ scale: 0.95 }}
                            className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--primary)/0.2)] transition-colors"
                        >
                            <ArrowLeft className="w-4 h-4" />
                            <span className="text-sm font-medium hidden sm:inline">Back</span>
                        </motion.button>
                    </Link>

                    {/* Breadcrumb */}
                    <div className="hidden md:flex items-center gap-2 text-sm">
                        <Link
                            href="/"
                            className="text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors flex items-center gap-1"
                        >
                            <Home className="w-3.5 h-3.5" />
                            <span>Tutorials</span>
                        </Link>
                        <span className="text-[hsl(var(--muted-foreground))]">/</span>
                        <span
                            className="font-medium"
                            style={{ color: accentColor }}
                        >
                            {codebaseName}
                        </span>
                        <span className="text-[hsl(var(--muted-foreground))]">/</span>
                        <span className="text-[hsl(var(--muted-foreground))] truncate max-w-[200px]">
                            {currentFileName}
                        </span>
                    </div>

                    {/* Mobile title */}
                    <div className="md:hidden">
                        <span
                            className="text-sm font-medium"
                            style={{ color: accentColor }}
                        >
                            {codebaseName}
                        </span>
                    </div>
                </div>

                {/* Right section - Actions */}
                <div className="flex items-center gap-2">
                    {/* Zoom controls (only in preview mode) */}
                    {!isEditMode && (
                        <>
                            <motion.button
                                whileHover={{ scale: 1.1 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={onZoomOut}
                                className="p-2 rounded-lg hover:bg-[hsl(var(--secondary))] transition-colors hidden sm:block"
                                title="Zoom out"
                            >
                                <ZoomOut className="w-4 h-4" />
                            </motion.button>
                            <motion.button
                                whileHover={{ scale: 1.1 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={onZoomIn}
                                className="p-2 rounded-lg hover:bg-[hsl(var(--secondary))] transition-colors hidden sm:block"
                                title="Zoom in"
                            >
                                <ZoomIn className="w-4 h-4" />
                            </motion.button>
                            <motion.button
                                whileHover={{ scale: 1.1 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={onFullscreen}
                                className="p-2 rounded-lg hover:bg-[hsl(var(--secondary))] transition-colors hidden sm:block"
                                title="Fullscreen"
                            >
                                <Maximize2 className="w-4 h-4" />
                            </motion.button>
                            <div className="w-px h-6 bg-[hsl(var(--border))] hidden sm:block" />
                        </>
                    )}

                    {/* Theme toggle */}
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={toggleTheme}
                        className="p-2 rounded-lg hover:bg-[hsl(var(--secondary))] transition-colors"
                        title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
                    >
                        {theme === 'dark' ? (
                            <Moon className="w-4 h-4" />
                        ) : (
                            <Sun className="w-4 h-4" />
                        )}
                    </motion.button>

                    <div className="w-px h-6 bg-[hsl(var(--border))]" />

                    {/* Edit/Preview toggle */}
                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={onToggleEditMode}
                        className="flex items-center gap-2 px-4 py-2 rounded-xl transition-all"
                        style={{
                            background: isEditMode
                                ? `linear-gradient(135deg, ${accentColor}, ${accentColor}80)`
                                : 'hsl(var(--secondary))',
                            color: isEditMode ? 'white' : 'inherit',
                            boxShadow: isEditMode ? `0 4px 15px ${accentColor}40` : 'none'
                        }}
                    >
                        {isEditMode ? (
                            <>
                                <Eye className="w-4 h-4" />
                                <span className="text-sm font-medium">Preview</span>
                            </>
                        ) : (
                            <>
                                <Edit3 className="w-4 h-4" />
                                <span className="text-sm font-medium">Edit</span>
                            </>
                        )}
                    </motion.button>
                </div>
            </div>

            {/* Keyboard shortcut hint */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1 }}
                className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-full mt-2 hidden lg:block"
            >
                <div className="text-xs text-[hsl(var(--muted-foreground))] bg-[hsl(var(--secondary))] px-3 py-1 rounded-full opacity-0 hover:opacity-100 transition-opacity">
                    Press <kbd className="px-1 py-0.5 mx-1 rounded bg-[hsl(var(--background))]">Ctrl+E</kbd> to toggle edit mode
                </div>
            </motion.div>
        </motion.div>
    );
}
