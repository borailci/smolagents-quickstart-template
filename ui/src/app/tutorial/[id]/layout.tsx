import { notFound } from "next/navigation";

// This layout doesn't use static params since we're using dynamic API routes
// The page.tsx handles data fetching via API calls

export default async function TutorialLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="flex h-[calc(100vh-7rem)] overflow-hidden">
            {children}
        </div>
    );
}
