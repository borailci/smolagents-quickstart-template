import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const DEEP_AGENT_OUTPUT_PATH = path.join(process.cwd(), '..', 'data', 'deep_agent_output');

export async function GET(request: NextRequest) {
    const searchParams = request.nextUrl.searchParams;
    const codebaseId = searchParams.get('codebase');
    const filename = searchParams.get('filename');

    if (!codebaseId || !filename) {
        return NextResponse.json(
            { error: 'Missing codebase or filename parameter' },
            { status: 400 }
        );
    }

    // Prevent path traversal attacks
    if (codebaseId.includes('..') || filename.includes('..')) {
        return NextResponse.json(
            { error: 'Invalid path' },
            { status: 400 }
        );
    }

    const filePath = path.join(DEEP_AGENT_OUTPUT_PATH, codebaseId, 'tutorials', filename);

    try {
        if (!fs.existsSync(filePath)) {
            return NextResponse.json(
                { error: `File not found: ${filename}` },
                { status: 404 }
            );
        }

        const content = fs.readFileSync(filePath, 'utf-8');
        return new NextResponse(content, {
            headers: {
                'Content-Type': 'text/markdown; charset=utf-8',
            },
        });
    } catch (error) {
        console.error('Error reading file:', error);
        return NextResponse.json(
            { error: String(error) },
            { status: 500 }
        );
    }
}
