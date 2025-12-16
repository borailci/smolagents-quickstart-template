'use client';

import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import mermaid from 'mermaid';

// Initialize mermaid with dark theme
mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    themeVariables: {
        primaryColor: '#8B5CF6',
        primaryTextColor: '#fff',
        primaryBorderColor: '#6D28D9',
        lineColor: '#64748B',
        secondaryColor: '#1E293B',
        tertiaryColor: '#0F172A',
    },
});

interface MarkdownViewerProps {
    content: string;
}

function MermaidDiagram({ code }: { code: string }) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [svg, setSvg] = useState<string>('');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const renderDiagram = async () => {
            try {
                // Sanitize Mermaid code: escape problematic characters in labels
                // Replace parentheses inside square brackets with safer alternatives
                let sanitized = code;
                // Replace [Label (text)] with [Label - text] to avoid parsing issues
                sanitized = sanitized.replace(
                    /\[([^\]]*?)\s*\(([^)]*)\)\s*([^\]]*?)\]/g,
                    '["$1 - $2$3"]'
                );
                // Also handle e.g., references in parentheses
                sanitized = sanitized.replace(
                    /\[([^\]]*?)\s*\(e\.g\.,?\s*([^)]*)\)\]/g,
                    '["$1 e.g. $2"]'
                );

                const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
                const { svg } = await mermaid.render(id, sanitized);
                setSvg(svg);
                setError(null);
            } catch (err) {
                setError('Failed to render diagram');
                console.error('Mermaid error:', err);
            }
        };
        renderDiagram();
    }, [code]);

    if (error) {
        return (
            <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-red-400">
                <p className="text-sm">{error}</p>
                <pre className="mt-2 text-xs text-slate-400">{code}</pre>
            </div>
        );
    }

    return (
        <div
            ref={containerRef}
            className="my-6 flex justify-center overflow-x-auto rounded-lg bg-slate-800/50 p-4"
            dangerouslySetInnerHTML={{ __html: svg }}
        />
    );
}

export function MarkdownViewer({ content }: MarkdownViewerProps) {
    return (
        <div className="prose prose-invert max-w-none prose-headings:text-white prose-p:text-slate-300 prose-a:text-violet-400 prose-strong:text-white prose-code:text-cyan-400 prose-pre:bg-transparent prose-pre:p-0">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    code({ className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '');
                        const language = match ? match[1] : '';
                        const codeString = String(children).replace(/\n$/, '');

                        // Handle Mermaid diagrams
                        if (language === 'mermaid') {
                            return <MermaidDiagram code={codeString} />;
                        }

                        // Inline code
                        if (!className) {
                            return (
                                <code className="rounded bg-slate-800 px-1.5 py-0.5 text-cyan-400" {...props}>
                                    {children}
                                </code>
                            );
                        }

                        // Code blocks with syntax highlighting
                        return (
                            <SyntaxHighlighter
                                style={oneDark}
                                language={language || 'text'}
                                PreTag="div"
                                className="rounded-lg"
                                customStyle={{
                                    margin: '1rem 0',
                                    padding: '1rem',
                                    borderRadius: '0.5rem',
                                    backgroundColor: '#1E293B',
                                }}
                            >
                                {codeString}
                            </SyntaxHighlighter>
                        );
                    },
                    table({ children }) {
                        return (
                            <div className="my-4 overflow-x-auto">
                                <table className="min-w-full border-collapse border border-slate-700">
                                    {children}
                                </table>
                            </div>
                        );
                    },
                    th({ children }) {
                        return (
                            <th className="border border-slate-700 bg-slate-800 px-4 py-2 text-left font-semibold text-white">
                                {children}
                            </th>
                        );
                    },
                    td({ children }) {
                        return (
                            <td className="border border-slate-700 px-4 py-2 text-slate-300">
                                {children}
                            </td>
                        );
                    },
                    blockquote({ children }) {
                        return (
                            <blockquote className="border-l-4 border-violet-500 pl-4 italic text-slate-400">
                                {children}
                            </blockquote>
                        );
                    },
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}
