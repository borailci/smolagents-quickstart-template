'use client';

import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Edit3, Eye, ZoomIn, ZoomOut } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface ToolbarProps {
    codebaseName: string;
    currentFile: string;
    isEditMode: boolean;
    onToggleEdit: () => void;
    onZoomIn: () => void;
    onZoomOut: () => void;
    accentColor: string;
}

export function Toolbar({
    codebaseName,
    currentFile,
    isEditMode,
    onToggleEdit,
    onZoomIn,
    onZoomOut,
    accentColor,
}: ToolbarProps) {
    const router = useRouter();

    return (
        <motion.div
            initial={{ y: -10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="flex items-center justify-between border-b border-white/10 bg-slate-900/80 px-6 py-3 backdrop-blur-lg"
        >
            {/* Left: Back + Breadcrumb */}
            <div className="flex items-center gap-4">
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => router.push('/')}
                    className="text-slate-400 hover:text-white"
                >
                    <ArrowLeft className="h-5 w-5" />
                </Button>
                <div className="flex items-center gap-2 text-sm">
                    <span className="text-slate-400">{codebaseName}</span>
                    <span className="text-slate-600">/</span>
                    <span className="text-white">{currentFile}</span>
                </div>
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-2">
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={onZoomOut}
                    className="text-slate-400 hover:text-white"
                >
                    <ZoomOut className="h-4 w-4" />
                </Button>
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={onZoomIn}
                    className="text-slate-400 hover:text-white"
                >
                    <ZoomIn className="h-4 w-4" />
                </Button>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={onToggleEdit}
                    className="gap-2 border-white/10 text-slate-300 hover:text-white"
                    style={{
                        backgroundColor: isEditMode ? `${accentColor}20` : undefined,
                        borderColor: isEditMode ? accentColor : undefined,
                    }}
                >
                    {isEditMode ? (
                        <>
                            <Eye className="h-4 w-4" />
                            Preview
                        </>
                    ) : (
                        <>
                            <Edit3 className="h-4 w-4" />
                            Edit
                        </>
                    )}
                </Button>
            </div>
        </motion.div>
    );
}
