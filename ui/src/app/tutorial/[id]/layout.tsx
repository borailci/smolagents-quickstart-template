import { getCodebaseById, getContentConfig } from "@/lib/config";
import { FileSidebar } from "@/components/FileSidebar";
import { notFound } from "next/navigation";

export async function generateStaticParams() {
    const config = getContentConfig();
    return config.codebases.map((c) => ({ id: c.id }));
}

export default async function TutorialLayout({
    children,
    params,
}: {
    children: React.ReactNode;
    params: Promise<{ id: string }>;
}) {
    const resolvedParams = await params;
    const codebase = getCodebaseById(resolvedParams.id);

    if (!codebase) {
        notFound();
    }

    return (
        <div className="flex h-[calc(100vh-7rem)] overflow-hidden">
            <FileSidebar codebase={codebase} />
            <div className="flex-1 ml-80 p-0 overflow-x-hidden">
                {children}
            </div>
        </div>
    );
}
