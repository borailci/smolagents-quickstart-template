# Codebase Tutorial Generator UI Guide

This guide explains how to set up, run, and customize the Tutorial Generator UI.

## 1. Prerequisites

- Node.js 18+  
- npm, pnpm, or yarn

## 2. Installation

Navigate to the UI directory and install dependencies:

```bash
cd ui
npm install
```

## 3. Configuration

### Environment Variables

Copy the example file:

```bash
cp .env.local.example .env.local
```

Edit `.env.local`:

```env
NEXT_PUBLIC_LOADING_DURATION_MS=3500
NEXT_PUBLIC_MARKDOWN_BASE_PATH="../"
NEXT_PUBLIC_DEVELOPER_1_NAME="Amir Kiarafi"
```

### Adding Documented Codebases

Edit `ui/content.yaml` to register new tutorials:

```yaml
codebases:
  - id: "my-new-project"
    name: "My New Project"
    description: "Description here"
    icon: "code"
    color: "#ff0000"
    files:
      - path: "tutorials/my-project/intro.md"
        title: "Introduction"
```

The `path` should be relative to the project root (where the Python scripts live), not the `ui` folder, assuming `NEXT_PUBLIC_MARKDOWN_BASE_PATH="../"`.

## 4. Running Locally

Start the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## 5. Building for Production

```bash
npm run build
npm start
```

## 6. Customization

- **Theme**: Edit `ui/src/app/globals.css` variable `--primary`, `--accent`.
- **Icons**: Update `IconMap` in `ui/src/components/CodebaseCard.tsx`.
- **Loading Animation**: Edit `ui/src/components/LoadingProgress.tsx` or change duration in env vars.

## 7. Troubleshooting

- **Mermaid diagrams not rendering**: Ensure the markdown code block language is exactly `mermaid`.
- **File not found**: Check `content.yaml` paths and ensure `NEXT_PUBLIC_MARKDOWN_BASE_PATH` is correct.
