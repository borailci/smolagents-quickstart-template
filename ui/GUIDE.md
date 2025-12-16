# Tutorial Generator UI - Setup Guide

## Prerequisites

- Node.js 18+ 
- npm 9+

## Quick Start

```bash
cd ui
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Configuration

### Environment Variables

Copy `.env.local.example` to `.env.local`:

```bash
cp .env.local.example .env.local
```

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_LOADING_DURATION_MS` | 3500 | Loading animation duration |
| `NEXT_PUBLIC_DEVELOPER_1_NAME` | - | Footer credit |
| `NEXT_PUBLIC_DEVELOPER_1_GITHUB` | - | GitHub profile URL |
| `NEXT_PUBLIC_REPO_URL` | - | Repository URL |

### Content Configuration

Edit `content.yaml` to add codebases:

```yaml
codebases:
  - id: "my-project"
    name: "My Project"
    description: "Project description"
    icon: "code"  # robot, code, folder, database, server, globe
    color: "#8B5CF6"
    files:
      - path: "docs/getting-started.md"
        title: "Getting Started"
```

## Production Build

```bash
npm run build
npm start
```

## Features

- **Mermaid.js diagrams** - flowcharts render automatically
- **Syntax highlighting** - code blocks with Prism
- **Edit mode** - `Cmd+E` to toggle
- **Dark theme** - default with toggle
- **Responsive** - mobile-friendly sidebar

## Troubleshooting

**Mermaid diagrams not rendering?**
- Diagrams render client-side only
- Check browser console for errors

**Build errors?**
- Run `npm run lint` to check for issues
- Ensure Node.js 18+
