import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

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

    let basePath = '';

    // Determine base path based on codebase ID
    if (codebaseId === 'deep_agent') {
        basePath = path.join(process.cwd(), '..', 'data', 'deep_agent', 'tutorials');
    } else if (codebaseId === 'baseline') {
        basePath = path.join(process.cwd(), '..', 'data', 'baseline', 'tutorials');
    } else {
        // Fallback for legacy or unknown paths (or standard structure)
        basePath = path.join(process.cwd(), '..', 'data', 'deep_agent_output', codebaseId, 'tutorials');
    }

    const filePath = path.join(basePath, filename);

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
