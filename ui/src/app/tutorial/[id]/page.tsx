
import { getCodebaseById, getTutorialContent } from "@/lib/config";
import { MarkdownViewer } from "@/components/MarkdownViewer";
import { notFound } from "next/navigation";

export default async function TutorialPage({
    params,
    searchParams,
}: {
    params: Promise<{ id: string }>;
    searchParams: Promise<{ file?: string }>;
}) {
    const resolvedParams = await params;
    const resolvedSearchParams = await searchParams;

    const codebase = getCodebaseById(resolvedParams.id);
    if (!codebase) return notFound();

    const currentFile = resolvedSearchParams.file
        ? codebase.files.find(f => f.path === resolvedSearchParams.file)
        : codebase.files[0];

    if (!currentFile) {
        return <div className="p-8 text-center text-red-400">File not found.</div>;
    }

    const content = getTutorialContent(currentFile.path);

    return (
        <div className="h-full">
            <MarkdownViewer
                initialContent={content}
                fileName={currentFile.title || currentFile.path}
            />
        </div>
    );
}
