'use client';

import { useRef, useState, useCallback, useEffect } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import { motion } from 'framer-motion';
import { Save, RotateCcw, Copy, Check } from 'lucide-react';

interface MarkdownEditorProps {
    content: string;
    onChange: (content: string) => void;
    onSave?: (content: string) => void;
    accentColor?: string;
}

export default function MarkdownEditor({
    content,
    onChange,
    onSave,
    accentColor = '#8B5CF6'
}: MarkdownEditorProps) {
    const editorRef = useRef<Parameters<OnMount>[0] | null>(null);
    const [originalContent] = useState(content);
    const [hasChanges, setHasChanges] = useState(false);
    const [saved, setSaved] = useState(false);
    const [copied, setCopied] = useState(false);

    const handleEditorDidMount: OnMount = (editor) => {
        editorRef.current = editor;
    };

    const handleEditorChange = useCallback((value: string | undefined) => {
        const newValue = value || '';
        onChange(newValue);
        setHasChanges(newValue !== originalContent);
        setSaved(false);
    }, [onChange, originalContent]);

    const handleSave = useCallback(() => {
        if (onSave && editorRef.current) {
            onSave(editorRef.current.getValue());
            setSaved(true);
            setTimeout(() => setSaved(false), 2000);
        }
    }, [onSave]);

    const handleReset = useCallback(() => {
        if (editorRef.current) {
            editorRef.current.setValue(originalContent);
            onChange(originalContent);
            setHasChanges(false);
        }
    }, [originalContent, onChange]);

    const handleCopy = useCallback(async () => {
        if (editorRef.current) {
            await navigator.clipboard.writeText(editorRef.current.getValue());
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    }, []);

    // Keyboard shortcuts
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                handleSave();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleSave]);

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="h-full flex flex-col rounded-xl overflow-hidden border border-[hsl(var(--border))]"
        >
            {/* Editor Toolbar */}
            <div className="flex items-center justify-between px-4 py-2 bg-[hsl(var(--secondary)/0.5)] border-b border-[hsl(var(--border))]">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-[hsl(var(--muted-foreground))]">
                        Markdown Editor
                    </span>
                    {hasChanges && (
                        <motion.span
                            initial={{ opacity: 0, scale: 0.8 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="text-xs px-2 py-0.5 rounded-full"
                            style={{
                                background: `${accentColor}20`,
                                color: accentColor
                            }}
                        >
                            Unsaved changes
                        </motion.span>
                    )}
                </div>

                <div className="flex items-center gap-2">
                    {/* Copy button */}
                    <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={handleCopy}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--secondary)/0.8)] transition-colors"
                    >
                        {copied ? (
                            <>
                                <Check className="w-4 h-4 text-green-500" />
                                <span className="text-green-500">Copied</span>
                            </>
                        ) : (
                            <>
                                <Copy className="w-4 h-4" />
                                <span>Copy</span>
                            </>
                        )}
                    </motion.button>

                    {/* Reset button */}
                    <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={handleReset}
                        disabled={!hasChanges}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--secondary)/0.8)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <RotateCcw className="w-4 h-4" />
                        <span>Reset</span>
                    </motion.button>

                    {/* Save button */}
                    <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={handleSave}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors"
                        style={{
                            background: saved ? '#10B981' : accentColor,
                            color: 'white'
                        }}
                    >
                        {saved ? (
                            <>
                                <Check className="w-4 h-4" />
                                <span>Saved!</span>
                            </>
                        ) : (
                            <>
                                <Save className="w-4 h-4" />
                                <span>Save</span>
                            </>
                        )}
                    </motion.button>
                </div>
            </div>

            {/* Monaco Editor */}
            <div className="flex-1">
                <Editor
                    height="100%"
                    defaultLanguage="markdown"
                    value={content}
                    onChange={handleEditorChange}
                    onMount={handleEditorDidMount}
                    theme="vs-dark"
                    options={{
                        fontSize: 14,
                        fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, monospace",
                        lineHeight: 1.6,
                        minimap: { enabled: true, scale: 1 },
                        wordWrap: 'on',
                        smoothScrolling: true,
                        cursorBlinking: 'smooth',
                        cursorSmoothCaretAnimation: 'on',
                        lineNumbers: 'on',
                        renderLineHighlight: 'all',
                        scrollBeyondLastLine: false,
                        automaticLayout: true,
                        padding: { top: 16, bottom: 16 },
                        folding: true,
                        foldingHighlight: true,
                        bracketPairColorization: { enabled: true },
                        guides: {
                            bracketPairs: true,
                            indentation: true,
                        },
                    }}
                />
            </div>

            {/* Status bar */}
            <div className="flex items-center justify-between px-4 py-1.5 bg-[hsl(var(--secondary)/0.3)] border-t border-[hsl(var(--border))] text-xs text-[hsl(var(--muted-foreground))]">
                <div className="flex items-center gap-4">
                    <span>Markdown</span>
                    <span>{content.split('\n').length} lines</span>
                    <span>{content.length} characters</span>
                </div>
                <div className="flex items-center gap-2">
                    <kbd className="px-1.5 py-0.5 rounded bg-[hsl(var(--secondary))] text-[10px]">
                        Ctrl+S
                    </kbd>
                    <span>to save</span>
                </div>
            </div>
        </motion.div>
    );
}
