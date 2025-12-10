"use client";

import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import Editor from "@monaco-editor/react";
import mermaid from "mermaid";
import { Button } from "@/components/ui/button"; // Need to create basic button or use html
import {
    Edit2,
    Eye,
    Save,
    Columns,
    Bold,
    Italic,
    List,
    Heading1,
    Heading2,
    Heading3,
    Code as CodeIcon,
    Link as LinkIcon
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

// Helper for Mermaid
mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    securityLevel: 'loose',
});

const Mermaid = ({ chart }: { chart: string }) => {
    const [svg, setSvg] = useState('');

    useEffect(() => {
        const render = async () => {
            try {
                const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
                const { svg } = await mermaid.render(id, chart);
                setSvg(svg);
            } catch (error) {
                console.error("Mermaid render error:", error);
                // setSvg('<div class="text-red-500">Failed to render diagram</div>');
            }
        };
        render();
    }, [chart]);

    return <div className="mermaid-diagram my-6 p-4 bg-white/5 rounded-lg overflow-x-auto text-center" dangerouslySetInnerHTML={{ __html: svg }} />;
};

interface MarkdownViewerProps {
    initialContent: string;
    fileName: string;
}

export function MarkdownViewer({ initialContent, fileName }: MarkdownViewerProps) {
    const [content, setContent] = useState(initialContent);
    const [viewMode, setViewMode] = useState<'preview' | 'edit' | 'split'>('preview');
    const editorRef = useRef<any>(null);

    // Sync content when prop changes (new file selected)
    useEffect(() => {
        setContent(initialContent);
        setViewMode('preview');
    }, [initialContent]);

    const handleEditorChange = (value: string | undefined) => {
        setContent(value || "");
    };

    const handleEditorDidMount = (editor: any) => {
        editorRef.current = editor;
    };

    const insertText = (before: string, after = "") => {
        const editor = editorRef.current;
        if (!editor) return;

        const selection = editor.getSelection();
        const model = editor.getModel();
        const text = model.getValueInRange(selection);

        const newText = `${before}${text}${after}`;

        editor.executeEdits(null, [{
            range: selection,
            text: newText,
            forceMoveMarkers: true
        }]);

        editor.focus();
    };

    const EditorToolbar = () => (
        <div className="flex items-center gap-1 p-2 border-b border-white/10 bg-white/5 overflow-x-auto">
            <button onClick={() => insertText("**", "**")} className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Bold">
                <Bold className="w-4 h-4" />
            </button>
            <button onClick={() => insertText("*", "*")} className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Italic">
                <Italic className="w-4 h-4" />
            </button>
            <div className="w-px h-4 bg-white/10 mx-1" />
            <button onClick={() => insertText("# ")} className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Heading 1">
                <Heading1 className="w-4 h-4" />
            </button>
            <button onClick={() => insertText("## ")} className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Heading 2">
                <Heading2 className="w-4 h-4" />
            </button>
            <button onClick={() => insertText("### ")} className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Heading 3">
                <Heading3 className="w-4 h-4" />
            </button>
            <div className="w-px h-4 bg-white/10 mx-1" />
            <button onClick={() => insertText("- ")} className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="List">
                <List className="w-4 h-4" />
            </button>
            <button onClick={() => insertText("```\n", "\n```")} className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Code Block">
                <CodeIcon className="w-4 h-4" />
            </button>
            <button onClick={() => insertText("[", "](url)")} className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Link">
                <LinkIcon className="w-4 h-4" />
            </button>
        </div>
    );

    const MarkdownPreview = () => (
        <article className="prose prose-invert prose-lg max-w-none prose-headings:text-purple-100 prose-a:text-cyan-400 prose-code:text-purple-300 hover:prose-a:underline h-full overflow-y-auto px-8 pt-8 custom-scrollbar">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    code({ node, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '');
                        const isMermaid = match && match[1] === 'mermaid';

                        if (isMermaid) {
                            return <Mermaid chart={String(children).replace(/\n$/, '')} />;
                        }

                        return match ? (
                            // @ts-ignore
                            <SyntaxHighlighter
                                {...props}
                                style={vscDarkPlus}
                                language={match[1]}
                                PreTag="div"
                                customStyle={{ background: '#0f172a', borderRadius: '0.5rem', padding: '1rem' }}
                            >
                                {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                        ) : (
                            <code {...props} className={className}>
                                {children}
                            </code>
                        );
                    },
                    h1: ({ node, ...props }) => <h1 className="text-4xl font-extrabold mb-8 bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-cyan-400" {...props} />,
                    blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-purple-500 pl-4 italic text-gray-400" {...props} />,
                }}
            >
                {content}
            </ReactMarkdown>
        </article>
    );

    return (
        <div className="flex flex-col h-full">
            {/* Toolbar - Compact */}
            <div className="flex items-center justify-between px-4 py-1.5 bg-background border-b border-white/5 shrink-0">
                <h1 className="text-xs font-bold truncate text-gray-400 font-mono">{fileName}</h1>

                <div className="flex items-center gap-1 bg-white/5 rounded-md p-0.5">
                    <button
                        onClick={() => setViewMode('preview')}
                        className={`flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-medium transition-colors ${viewMode === 'preview' ? 'bg-primary text-white shadow-sm' : 'text-gray-400 hover:text-gray-200'}`}
                    >
                        <Eye className="w-3 h-3" /> Preview
                    </button>
                    <button
                        onClick={() => setViewMode('split')}
                        className={`flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-medium transition-colors ${viewMode === 'split' ? 'bg-primary text-white shadow-sm' : 'text-gray-400 hover:text-gray-200'}`}
                    >
                        <Columns className="w-3 h-3" /> Split
                    </button>
                    <button
                        onClick={() => setViewMode('edit')}
                        className={`flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-medium transition-colors ${viewMode === 'edit' ? 'bg-primary text-white shadow-sm' : 'text-gray-400 hover:text-gray-200'}`}
                    >
                        <Edit2 className="w-3 h-3" /> Edit
                    </button>

                    {viewMode !== 'preview' && (
                        <>
                            <div className="w-px h-3 bg-white/10 mx-1" />
                            <button className="flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-medium bg-green-600/20 text-green-400 hover:bg-green-600/30 transition-colors border border-green-600/20">
                                <Save className="w-3 h-3" /> Save
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* Content Area */}
            <div className={`flex-1 overflow-hidden min-h-0 ${viewMode === 'preview' ? 'max-w-5xl mx-auto w-full' : ''}`}>
                {viewMode === 'preview' && <MarkdownPreview />}

                {viewMode === 'edit' && (
                    <div className="h-full flex flex-col">
                        <EditorToolbar />
                        <div className="flex-1">
                            <Editor
                                height="100%"
                                defaultLanguage="markdown"
                                theme="vs-dark"
                                value={content}
                                onChange={handleEditorChange}
                                onMount={handleEditorDidMount}
                                options={{
                                    minimap: { enabled: false },
                                    fontSize: 14,
                                    lineNumbers: "on",
                                    scrollBeyondLastLine: false,
                                    wordWrap: "on",
                                    padding: { top: 16, bottom: 16 }
                                }}
                            />
                        </div>
                    </div>
                )}

                {viewMode === 'split' && (
                    <div className="grid grid-cols-2 h-full divide-x divide-white/10">
                        <div className="flex flex-col h-full bg-[#1e1e1e]">
                            <EditorToolbar />
                            <div className="flex-1">
                                <Editor
                                    height="100%"
                                    defaultLanguage="markdown"
                                    theme="vs-dark"
                                    value={content}
                                    onChange={handleEditorChange}
                                    onMount={handleEditorDidMount}
                                    options={{
                                        minimap: { enabled: false },
                                        fontSize: 13,
                                        lineNumbers: "on",
                                        scrollBeyondLastLine: false,
                                        wordWrap: "on",
                                        padding: { top: 16 }
                                    }}
                                />
                            </div>
                        </div>
                        <div className="h-full overflow-hidden bg-background">
                            <MarkdownPreview />
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
