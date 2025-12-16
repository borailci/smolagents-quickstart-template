import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

// Path to deep agent output directory (relative to project root)
const DEEP_AGENT_OUTPUT_PATH = path.join(process.cwd(), '..', 'data', 'deep_agent_output');

interface CodebaseInfo {
    id: string;
    name: string;
    description: string;
    tutorialCount: number;
    tutorials: { filename: string; title: string }[];
}

function extractTitle(content: string, filename: string): string {
    // Split into lines and find the first real markdown heading
    // (excluding code block comments which might start with #)
    const lines = content.split('\n');
    let inCodeBlock = false;

    for (const line of lines) {
        // Track code block boundaries
        if (line.trim().startsWith('```')) {
            inCodeBlock = !inCodeBlock;
            continue;
        }

        // Skip if we're inside a code block
        if (inCodeBlock) continue;

        // Check for H1-H3 heading (must be at line start, with space after #)
        const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
        if (headingMatch) {
            // Remove backticks from title for clean display
            return headingMatch[2].trim().replace(/`/g, '');
        }
    }

    // Fallback: humanize filename
    return filename
        .replace(/^\d+_/, '')
        .replace(/\.md$/, '')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

function humanizeName(id: string): string {
    return id
        .replace(/_/g, ' ')
        .replace(/-/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

export async function GET() {
    try {
        if (!fs.existsSync(DEEP_AGENT_OUTPUT_PATH)) {
            return NextResponse.json({ codebases: [], error: 'Output directory not found' });
        }

        const codebases: CodebaseInfo[] = [];
        const entries = fs.readdirSync(DEEP_AGENT_OUTPUT_PATH, { withFileTypes: true });

        for (const entry of entries) {
            if (!entry.isDirectory()) continue;

            const codebaseId = entry.name;
            const tutorialsPath = path.join(DEEP_AGENT_OUTPUT_PATH, codebaseId, 'tutorials');

            if (!fs.existsSync(tutorialsPath)) continue;

            const tutorials: { filename: string; title: string }[] = [];
            const tutorialFiles = fs.readdirSync(tutorialsPath)
                .filter(f => f.endsWith('.md'))
                .sort();

            for (const filename of tutorialFiles) {
                const filePath = path.join(tutorialsPath, filename);
                const content = fs.readFileSync(filePath, 'utf-8');
                tutorials.push({
                    filename,
                    title: extractTitle(content, filename),
                });
            }

            if (tutorials.length > 0) {
                codebases.push({
                    id: codebaseId,
                    name: humanizeName(codebaseId),
                    description: `${tutorials.length} tutorials generated for ${codebaseId}`,
                    tutorialCount: tutorials.length,
                    tutorials,
                });
            }
        }

        return NextResponse.json({ codebases });
    } catch (error) {
        console.error('Error reading codebases:', error);
        return NextResponse.json({ codebases: [], error: String(error) }, { status: 500 });
    }
}
