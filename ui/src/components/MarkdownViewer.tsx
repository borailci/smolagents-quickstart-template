'use client';

import { useState, useEffect, useRef, ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import mermaid from 'mermaid';
import { Check, Copy, Info, Lightbulb, AlertTriangle, AlertCircle } from 'lucide-react';

// Initialize mermaid with dark theme
mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    suppressErrorRendering: true, // Hide syntax error messages from page
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

// Copy button component
function CopyButton({ code }: { code: string }) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <button
            onClick={handleCopy}
            className="absolute right-2 top-2 rounded-md bg-slate-700/80 p-1.5 text-slate-400 opacity-0 transition-all hover:bg-slate-600 hover:text-white group-hover:opacity-100"
            title="Copy code"
        >
            {copied ? <Check className="h-4 w-4 text-green-400" /> : <Copy className="h-4 w-4" />}
        </button>
    );
}

// Callout component for GitHub-style alerts
function Callout({ type, children }: { type: 'note' | 'tip' | 'important' | 'warning' | 'caution'; children: ReactNode }) {
    const styles = {
        note: { icon: Info, bg: 'bg-blue-500/10', border: 'border-blue-500/30', text: 'text-blue-400', title: 'Note' },
        tip: { icon: Lightbulb, bg: 'bg-green-500/10', border: 'border-green-500/30', text: 'text-green-400', title: 'Tip' },
        important: { icon: AlertCircle, bg: 'bg-violet-500/10', border: 'border-violet-500/30', text: 'text-violet-400', title: 'Important' },
        warning: { icon: AlertTriangle, bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-400', title: 'Warning' },
        caution: { icon: AlertTriangle, bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400', title: 'Caution' },
    };

    const style = styles[type];
    const Icon = style.icon;

    return (
        <div className={`my-4 rounded-lg border ${style.border} ${style.bg} p-4`}>
            <div className={`mb-2 flex items-center gap-2 font-semibold ${style.text}`}>
                <Icon className="h-5 w-5" />
                {style.title}
            </div>
            <div className="text-slate-300">{children}</div>
        </div>
    );
}

function MermaidDiagram({ code }: { code: string }) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [svg, setSvg] = useState<string>('');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const renderDiagram = async () => {
            try {
                let sanitized = code;
                sanitized = sanitized.replace(
                    /\[([^\]]*?)\s*\(([^)]*)\)\s*([^\]]*?)\]/g,
                    '["$1 - $2$3"]'
                );
                sanitized = sanitized.replace(
                    /\[([^\]]*?)\s*\(e\.g\.,?\s*([^)]*)\)/g,
                    '["$1 e.g. $2"]'
                );

                const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
                const { svg } = await mermaid.render(id, sanitized);
                setSvg(svg);
                setError(null);
            } catch (err) {
                // Silently fail - don't show error boxes for invalid mermaid
                setError('Failed to render diagram');
                console.warn('Mermaid error:', err);
            }
        };
        renderDiagram();
    }, [code]);

    // Silently skip failed diagrams instead of showing error boxes
    if (error || !svg) {
        return null;
    }

    return (
        <div
            ref={containerRef}
            className="my-6 flex justify-center overflow-x-auto rounded-lg bg-slate-800/50 p-4"
            dangerouslySetInnerHTML={{ __html: svg }}
        />
    );
}

// Parse callouts from blockquote content
function parseCallout(text: string): { type: 'note' | 'tip' | 'important' | 'warning' | 'caution'; content: string } | null {
    const match = text.match(/^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*([\s\S]*)/i);
    if (match) {
        return {
            type: match[1].toLowerCase() as 'note' | 'tip' | 'important' | 'warning' | 'caution',
            content: match[2].trim()
        };
    }
    return null;
}

export function MarkdownViewer({ content }: MarkdownViewerProps) {
    return (
        <div className="prose prose-invert w-full max-w-full overflow-hidden break-words prose-headings:text-white prose-p:text-slate-300 prose-a:text-violet-400 prose-strong:text-white prose-code:text-cyan-400 prose-pre:bg-transparent prose-pre:p-0 prose-pre:max-w-full prose-pre:overflow-x-auto prose-code:before:content-none prose-code:after:content-none">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    //@ts-ignore
                    code({ node, inline, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '');
                        const language = match ? match[1] : '';
                        const codeString = String(children).replace(/\n$/, '');

                        // Handle Mermaid diagrams
                        if (!inline && language === 'mermaid') {
                            return <MermaidDiagram code={codeString} />;
                        }

                        const isInline = inline ?? (!match && !String(children).includes('\n'));

                        // Inline code
                        if (isInline) {
                            return (
                                <code className="rounded bg-slate-800 px-1.5 py-0.5 text-cyan-400" {...props}>
                                    {children}
                                </code>
                            );
                        }

                        // Code blocks with syntax highlighting and copy button
                        return (
                            <div className="group relative">
                                <CopyButton code={codeString} />
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
                            </div>
                        );
                    },
                    blockquote({ children }) {
                        // Check if it's a GitHub-style callout
                        const textContent = String(children?.toString() || '');
                        const callout = parseCallout(textContent);

                        if (callout) {
                            return <Callout type={callout.type}>{callout.content}</Callout>;
                        }

                        // Regular blockquote
                        return (
                            <blockquote className="border-l-4 border-violet-500 pl-4 italic text-slate-400">
                                {children}
                            </blockquote>
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
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}
