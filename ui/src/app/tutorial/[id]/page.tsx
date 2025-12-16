'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { FileSidebar } from '@/components/FileSidebar';
import { MarkdownViewer } from '@/components/MarkdownViewer';
import { Toolbar } from '@/components/Toolbar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2 } from 'lucide-react';

interface Tutorial {
    filename: string;
    title: string;
}

interface Codebase {
    id: string;
    name: string;
    tutorials: Tutorial[];
}

const codebaseColors: Record<string, string> = {
    deepagents: '#8B5CF6',
    default: '#06B6D4',
};

export default function TutorialPage() {
    const params = useParams();
    const id = params.id as string;

    const [codebase, setCodebase] = useState<Codebase | null>(null);
    const [activeFile, setActiveFile] = useState<string>('');
    const [content, setContent] = useState<string>('');
    const [isEditMode, setIsEditMode] = useState(false);
    const [zoom, setZoom] = useState(100);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const accentColor = codebaseColors[id] || codebaseColors.default;

    // Load codebase info
    useEffect(() => {
        fetch('/api/codebases')
            .then(res => res.json())
            .then(data => {
                const found = data.codebases?.find((cb: Codebase) => cb.id === id);
                if (found) {
                    setCodebase(found);
                    if (found.tutorials.length > 0) {
                        setActiveFile(found.tutorials[0].filename);
                    }
                } else {
                    setError(`Codebase "${id}" not found`);
                }
                setIsLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setIsLoading(false);
            });
    }, [id]);

    // Load file content
    useEffect(() => {
        if (!activeFile || !id) return;

        setIsLoading(true);
        fetch(`/api/file?codebase=${encodeURIComponent(id)}&filename=${encodeURIComponent(activeFile)}`)
            .then(res => {
                if (!res.ok) throw new Error(`Failed to load ${activeFile}`);
                return res.text();
            })
            .then(text => {
                setContent(text);
                setIsLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setIsLoading(false);
            });
    }, [activeFile, id]);

    // Keyboard shortcut for edit mode
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'e') {
                e.preventDefault();
                setIsEditMode(prev => !prev);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    const handleZoomIn = useCallback(() => setZoom(z => Math.min(z + 10, 150)), []);
    const handleZoomOut = useCallback(() => setZoom(z => Math.max(z - 10, 70)), []);

    if (isLoading && !codebase) {
        return (
            <div className="flex h-screen items-center justify-center gap-3">
                <Loader2 className="h-6 w-6 animate-spin text-violet-400" />
                <p className="text-slate-400">Loading...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex h-screen items-center justify-center">
                <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-6 text-red-400">
                    {error}
                </div>
            </div>
        );
    }

    if (!codebase) {
        return null;
    }

    const currentFileTitle = codebase.tutorials.find(t => t.filename === activeFile)?.title || activeFile;

    return (
        <div className="flex h-[calc(100vh-4rem)] flex-col">
            <Toolbar
                codebaseName={codebase.name}
                currentFile={currentFileTitle}
                isEditMode={isEditMode}
                onToggleEdit={() => setIsEditMode(!isEditMode)}
                onZoomIn={handleZoomIn}
                onZoomOut={handleZoomOut}
                accentColor={accentColor}
            />

            <div className="flex flex-1 overflow-hidden">
                <FileSidebar
                    files={codebase.tutorials.map(t => ({ path: t.filename, title: t.title }))}
                    activeFile={activeFile}
                    onFileSelect={setActiveFile}
                    accentColor={accentColor}
                />

                <motion.div
                    className="flex-1 overflow-hidden"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                >
                    <ScrollArea className="h-full">
                        <div
                            className="mx-auto max-w-4xl p-8"
                            style={{ fontSize: `${zoom}%` }}
                        >
                            {isLoading ? (
                                <div className="flex items-center justify-center py-20">
                                    <Loader2 className="h-8 w-8 animate-spin text-violet-400" />
                                </div>
                            ) : isEditMode ? (
                                <div className="rounded-lg border border-white/10 bg-slate-900 p-4">
                                    <textarea
                                        value={content}
                                        onChange={e => setContent(e.target.value)}
                                        className="h-[60vh] w-full resize-none bg-transparent font-mono text-sm text-slate-300 focus:outline-none"
                                    />
                                </div>
                            ) : (
                                <MarkdownViewer content={content} />
                            )}
                        </div>
                    </ScrollArea>
                </motion.div>
            </div>
        </div>
    );
}
