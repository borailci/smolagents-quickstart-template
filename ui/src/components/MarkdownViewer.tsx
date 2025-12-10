'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import mermaid from 'mermaid';
import { motion, AnimatePresence } from 'framer-motion';
import { Copy, Check, ZoomIn, ZoomOut, RotateCcw, Maximize2 } from 'lucide-react';

interface MarkdownViewerProps {
    content: string;
    accentColor?: string;
}

// Initialize mermaid with dark theme
mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    themeVariables: {
        primaryColor: '#8B5CF6',
        primaryTextColor: '#fff',
        primaryBorderColor: '#7C3AED',
        lineColor: '#6366F1',
        secondaryColor: '#1E293B',
        tertiaryColor: '#0F172A',
        background: '#0F172A',
        mainBkg: '#1E293B',
        nodeBorder: '#6366F1',
    },
    fontFamily: 'Inter, sans-serif',
});

// Mermaid diagram component with zoom functionality
function MermaidDiagram({ code }: { code: string }) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [svg, setSvg] = useState<string>('');
    const [scale, setScale] = useState(1);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const renderDiagram = async () => {
            try {
                const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
                const { svg } = await mermaid.render(id, code);
                setSvg(svg);
                setError(null);
            } catch (err) {
                console.error('Mermaid render error:', err);
                setError('Failed to render diagram');
            }
        };
        renderDiagram();
    }, [code]);

    const handleZoomIn = () => setScale(prev => Math.min(prev + 0.25, 3));
    const handleZoomOut = () => setScale(prev => Math.max(prev - 0.25, 0.5));
    const handleReset = () => setScale(1);

    if (error) {
        return (
            <div className="mermaid-container p-6 text-center">
                <p className="text-red-400 mb-2">⚠️ {error}</p>
                <pre className="text-xs text-[hsl(var(--muted-foreground))] overflow-auto">
                    {code}
                </pre>
            </div>
        );
    }

    return (
        <>
            <div className="mermaid-container relative group">
                {/* Zoom controls */}
                <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={handleZoomOut}
                        className="p-1.5 rounded-lg bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--primary)/0.2)] transition-colors"
                        title="Zoom out"
                    >
                        <ZoomOut className="w-4 h-4" />
                    </motion.button>
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={handleReset}
                        className="p-1.5 rounded-lg bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--primary)/0.2)] transition-colors"
                        title="Reset zoom"
                    >
                        <RotateCcw className="w-4 h-4" />
                    </motion.button>
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={handleZoomIn}
                        className="p-1.5 rounded-lg bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--primary)/0.2)] transition-colors"
                        title="Zoom in"
                    >
                        <ZoomIn className="w-4 h-4" />
                    </motion.button>
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => setIsFullscreen(true)}
                        className="p-1.5 rounded-lg bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--primary)/0.2)] transition-colors"
                        title="Fullscreen"
                    >
                        <Maximize2 className="w-4 h-4" />
                    </motion.button>
                </div>

                {/* Diagram */}
                <div
                    ref={containerRef}
                    className="mermaid overflow-auto"
                    style={{
                        transform: `scale(${scale})`,
                        transformOrigin: 'center center',
                        transition: 'transform 0.2s ease'
                    }}
                    dangerouslySetInnerHTML={{ __html: svg }}
                />

                {/* Zoom indicator */}
                <div className="absolute bottom-2 right-2 text-xs text-[hsl(var(--muted-foreground))] opacity-0 group-hover:opacity-100 transition-opacity">
                    {Math.round(scale * 100)}%
                </div>
            </div>

            {/* Fullscreen modal */}
            <AnimatePresence>
                {isFullscreen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 bg-[hsl(var(--background))/0.95] flex items-center justify-center p-8"
                        onClick={() => setIsFullscreen(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.9 }}
                            animate={{ scale: 1 }}
                            exit={{ scale: 0.9 }}
                            className="max-w-full max-h-full overflow-auto"
                            dangerouslySetInnerHTML={{ __html: svg }}
                        />
                        <button
                            onClick={() => setIsFullscreen(false)}
                            className="absolute top-4 right-4 p-2 rounded-lg bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--primary)/0.2)] transition-colors"
                        >
                            ✕
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}

// Code block with copy functionality
function CodeBlock({ language, children }: { language: string; children: string }) {
    const [copied, setCopied] = useState(false);

    const handleCopy = useCallback(async () => {
        await navigator.clipboard.writeText(children);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    }, [children]);

    // Handle mermaid diagrams
    if (language === 'mermaid') {
        return <MermaidDiagram code={children} />;
    }

    return (
        <div className="relative group">
            {/* Language badge & copy button */}
            <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-4 py-2 text-xs text-[hsl(var(--muted-foreground))]">
                <span className="uppercase font-medium">{language || 'text'}</span>
                <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={handleCopy}
                    className="p-1.5 rounded-lg bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--primary)/0.2)] transition-colors opacity-0 group-hover:opacity-100"
                >
                    {copied ? (
                        <Check className="w-4 h-4 text-green-500" />
                    ) : (
                        <Copy className="w-4 h-4" />
                    )}
                </motion.button>
            </div>

            <SyntaxHighlighter
                language={language || 'text'}
                style={oneDark}
                customStyle={{
                    margin: 0,
                    padding: '2.5rem 1rem 1rem 1rem',
                    borderRadius: '0.75rem',
                    fontSize: '0.875rem',
                    background: 'hsl(222.2 84% 6%)',
                }}
                showLineNumbers
                lineNumberStyle={{
                    minWidth: '2.5em',
                    paddingRight: '1em',
                    color: 'hsl(215 20.2% 35%)',
                }}
            >
                {children}
            </SyntaxHighlighter>
        </div>
    );
}

export default function MarkdownViewer({ content, accentColor = '#8B5CF6' }: MarkdownViewerProps) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="markdown-body"
        >
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    code({ className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '');
                        const language = match ? match[1] : '';
                        const isInline = !match;

                        if (isInline) {
                            return (
                                <code className={className} {...props}>
                                    {children}
                                </code>
                            );
                        }

                        return (
                            <CodeBlock language={language}>
                                {String(children).replace(/\n$/, '')}
                            </CodeBlock>
                        );
                    },
                    a({ href, children }) {
                        return (
                            <a
                                href={href}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-[hsl(var(--accent))] hover:text-[hsl(var(--primary))] transition-colors underline underline-offset-2"
                            >
                                {children}
                            </a>
                        );
                    },
                    h1({ children }) {
                        return (
                            <motion.h1
                                initial={{ opacity: 0, x: -20 }}
                                whileInView={{ opacity: 1, x: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.5 }}
                            >
                                {children}
                            </motion.h1>
                        );
                    },
                    h2({ children }) {
                        return (
                            <motion.h2
                                initial={{ opacity: 0, x: -20 }}
                                whileInView={{ opacity: 1, x: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.5 }}
                                style={{ borderColor: accentColor }}
                            >
                                {children}
                            </motion.h2>
                        );
                    },
                    blockquote({ children }) {
                        return (
                            <motion.blockquote
                                initial={{ opacity: 0, x: -10 }}
                                whileInView={{ opacity: 1, x: 0 }}
                                viewport={{ once: true }}
                                style={{ borderColor: accentColor }}
                            >
                                {children}
                            </motion.blockquote>
                        );
                    },
                }}
            >
                {content}
            </ReactMarkdown>
        </motion.div>
    );
}
