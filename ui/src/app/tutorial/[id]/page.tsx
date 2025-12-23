import { getCodebaseById } from '@/lib/config';
import TutorialClient from './TutorialClient';
import { notFound } from 'next/navigation';

export default async function TutorialPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    const codebase = getCodebaseById(id);

    if (!codebase) {
        return notFound();
    }

    return <TutorialClient codebase={codebase} id={id} />;
}
