import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

// Paths relative to project root (where next.js is running)
// Assuming next.js is in /ui/ and data is in /data/
// so we go up two levels: ../../data
// BUT code says process.cwd() which in nextjs usually points to project root if run from there?
// The user runs `npm run dev` in `ui/`.
// So process.cwd() is `/.../ui`.
// Data is at `../data`.

const DATA_ROOT = path.join(process.cwd(), '..', 'data');
const DEEP_AGENT_ROOT = path.join(DATA_ROOT, 'deep_agent', 'tutorials');
const BASELINE_ROOT = path.join(DATA_ROOT, 'baseline', 'tutorials');

interface CodebaseInfo {
    id: string;
    name: string;
    description: string;
    tutorialCount: number;
    tutorials: { filename: string; title: string }[];
}

function extractTitle(content: string, filename: string): string {
    const lines = content.split('\n');
    let inCodeBlock = false;

    for (const line of lines) {
        if (line.trim().startsWith('```')) {
            inCodeBlock = !inCodeBlock;
            continue;
        }
        if (inCodeBlock) continue;

        const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
        if (headingMatch) {
            return headingMatch[2].trim().replace(/`/g, '');
        }
    }

    return filename
        .replace(/^\d+_/, '')
        .replace(/\.md$/, '')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

function getTutorialsFromDir(dirPath: string): { filename: string; title: string }[] {
    if (!fs.existsSync(dirPath)) return [];

    return fs.readdirSync(dirPath)
        .filter(f => f.endsWith('.md'))
        .sort()
        .map(filename => {
            const content = fs.readFileSync(path.join(dirPath, filename), 'utf-8');
            return {
                filename,
                title: extractTitle(content, filename)
            };
        });
}

export async function GET() {
    try {
        const codebases: CodebaseInfo[] = [];

        // 1. Deep Agent Tutorials
        const deepTutorials = getTutorialsFromDir(DEEP_AGENT_ROOT);
        if (deepTutorials.length > 0) {
            codebases.push({
                id: 'deep_agent',
                name: 'Deep Agent',
                description: 'Tutorials generated with Knowledge Base + Supervisor strategy.',
                tutorialCount: deepTutorials.length,
                tutorials: deepTutorials,
            });
        }

        // 2. Baseline Tutorials
        const baselineTutorials = getTutorialsFromDir(BASELINE_ROOT);
        if (baselineTutorials.length > 0) {
            codebases.push({
                id: 'baseline',
                name: 'Baseline',
                description: 'Tutorials generated from raw codebase exploration (No KB).',
                tutorialCount: baselineTutorials.length,
                tutorials: baselineTutorials,
            });
        }

        return NextResponse.json({ codebases });
    } catch (error) {
        console.error('Error reading codebases:', error);
        return NextResponse.json({ codebases: [], error: String(error) }, { status: 500 });
    }
}
