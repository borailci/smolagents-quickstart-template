# 📚 Codebase Tutorial Generator UI - Setup Guide

Welcome to the UI for the Codebase Tutorial Generator! This guide will walk you through everything you need to know to set up, run, and customize the web interface.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Adding New Tutorials](#adding-new-tutorials)
- [Customization](#customization)
- [Development](#development)
- [Production Build](#production-build)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js**: Version 18.0 or higher ([Download](https://nodejs.org/))
- **npm**: Comes with Node.js (or use yarn/pnpm if preferred)

Verify your installation:

```bash
node --version  # Should output v18.x.x or higher
npm --version   # Should output 9.x.x or higher
```

---

## Quick Start

### 1. Navigate to the UI Directory

```bash
cd ui
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Set Up Environment Variables

Copy the example environment file:

```bash
cp .env.local.example .env.local
```

### 4. Start the Development Server

```bash
npm run dev
```

### 5. Open in Browser

Navigate to [http://localhost:3000](http://localhost:3000) to view the application.

---

## Configuration

### Environment Variables

Edit `.env.local` to customize the application:

| Variable                          | Description                                | Default                            |
| --------------------------------- | ------------------------------------------ | ---------------------------------- |
| `NEXT_PUBLIC_LOADING_DURATION_MS` | Loading animation duration in milliseconds | `3500`                             |
| `NEXT_PUBLIC_DEVELOPER_1_NAME`    | First developer's name                     | `Amir Kiarafi`                     |
| `NEXT_PUBLIC_DEVELOPER_1_GITHUB`  | First developer's GitHub URL               | `https://github.com/amirkiarafiei` |
| `NEXT_PUBLIC_DEVELOPER_2_NAME`    | Second developer's name                    | `Bora Ilci`                        |
| `NEXT_PUBLIC_DEVELOPER_2_GITHUB`  | Second developer's GitHub URL              | `https://github.com/borailci`      |
| `NEXT_PUBLIC_REPO_URL`            | Project repository URL                     | See .env file                      |

#### Example: Changing Loading Duration

To make the loading animation last 5 seconds:

```env
NEXT_PUBLIC_LOADING_DURATION_MS=5000
```

### Content Configuration

All tutorials are configured in `src/lib/config.ts`. This file defines:

- Available codebases/tutorials
- Tutorial metadata (name, description, icon, color)
- Markdown file paths for each tutorial

---

## Adding New Tutorials

### Step 1: Update Configuration

Edit `src/lib/config.ts` to add your codebase:

```typescript
{
  id: "my-project",
  name: "My Amazing Project",
  description: "Learn how my project works",
  icon: "Code",  // Lucide icon name
  color: "#8B5CF6",  // Accent color (hex)
  files: [
    {
      path: "/tutorials/my-project/intro.md",
      title: "Introduction"
    },
    {
      path: "/tutorials/my-project/getting-started.md",
      title: "Getting Started"
    }
  ]
}
```

### Step 2: Add Markdown Content

For now, content is embedded in the tutorial page component. In production, you would:

1. Create markdown files in `public/tutorials/your-project/`
2. Update the content loading logic to fetch from these files

### Available Icons

The following Lucide icons are available:
- `Bot` - AI/Robot
- `Link` - Connections
- `Cpu` - Processing
- `Flame` - Performance
- `Database` - Data storage
- `Code` - Programming
- `Sparkles` - AI Magic

### Color Palette Suggestions

| Color  | Hex       | Use Case       |
| ------ | --------- | -------------- |
| Purple | `#8B5CF6` | AI/ML projects |
| Cyan   | `#06B6D4` | Data/Cloud     |
| Pink   | `#EC4899` | Creative       |
| Orange | `#F97316` | Performance    |
| Green  | `#10B981` | Success/Growth |
| Blue   | `#3B82F6` | General tech   |

---

## Customization

### Changing the Theme

The application supports dark and light themes. Customize colors in `src/app/globals.css`:

```css
:root {
  /* Dark theme colors */
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
  --primary: 263.4 70% 50.4%;  /* Purple accent */
  --accent: 191 91% 36.5%;      /* Cyan accent */
  /* ... more variables */
}

.light {
  /* Light theme colors */
  --background: 0 0% 100%;
  /* ... */
}
```

### Changing Fonts

Fonts are configured in `src/app/layout.tsx`:

```typescript
import { Inter } from "next/font/google";

const inter = Inter({ 
  subsets: ["latin"],
  variable: "--font-inter",
});
```

To use a different font, import it from `next/font/google`:

```typescript
import { Outfit } from "next/font/google";

const outfit = Outfit({ 
  subsets: ["latin"],
  variable: "--font-outfit",
});
```

### Modifying Animations

Animations are powered by Framer Motion. Key files:
- `src/components/LoadingProgress.tsx` - Loading animation
- `src/components/CodebaseCard.tsx` - Card hover effects
- `src/app/page.tsx` - Page animations

---

## Development

### Project Structure

```
ui/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Landing page
│   │   ├── globals.css         # Global styles
│   │   └── tutorial/[id]/      # Tutorial pages
│   ├── components/             # React components
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   ├── CodebaseCard.tsx
│   │   ├── LoadingProgress.tsx
│   │   ├── FileSidebar.tsx
│   │   ├── MarkdownViewer.tsx
│   │   ├── MarkdownEditor.tsx
│   │   └── Toolbar.tsx
│   ├── lib/                    # Utilities
│   │   ├── config.ts           # Content configuration
│   │   └── utils.ts            # Helper functions
│   ├── hooks/                  # Custom hooks
│   │   └── useTheme.tsx        # Theme management
│   └── types/                  # TypeScript types
│       └── index.ts
├── .env.local                  # Environment variables
├── .env.local.example          # Example env file
├── package.json
└── GUIDE.md                    # This file
```

### Useful Commands

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linting
npm run lint

# Type check
npx tsc --noEmit
```

### Adding New Components

1. Create the component in `src/components/`
2. Use TypeScript interfaces for props
3. Add Framer Motion for animations
4. Follow the existing naming conventions

---

## Production Build

### Building the Application

```bash
npm run build
```

This creates an optimized production build in `.next/`.

### Running in Production

```bash
npm start
```

The application will be available at `http://localhost:3000`.

### Deploying

The UI can be deployed to:

- **Vercel** (Recommended): Push to GitHub and connect to Vercel
- **Netlify**: Use the Next.js adapter
- **Docker**: Create a Dockerfile for containerized deployment
- **Static Export**: Use `next export` for static hosting

#### Vercel Deployment

1. Push your code to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Import your repository
4. Vercel will auto-detect Next.js settings
5. Set environment variables in the Vercel dashboard
6. Deploy!

---

## Troubleshooting

### Common Issues

#### 1. "Module not found" errors

```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### 2. Mermaid diagrams not rendering

- Ensure mermaid is installed: `npm install mermaid`
- Check browser console for errors
- Mermaid requires client-side rendering

#### 3. Monaco Editor not loading

- Monaco Editor is lazy-loaded
- Check network tab for blocked resources
- Try refreshing the page

#### 4. Theme not persisting

- Clear localStorage: `localStorage.clear()`
- Check for browser extensions blocking storage

#### 5. Build errors with TypeScript

```bash
# Check for type errors
npx tsc --noEmit

# Ignore type errors temporarily (not recommended)
# Add to next.config.js:
# typescript: { ignoreBuildErrors: true }
```

### Getting Help

If you encounter issues:

1. Check the browser console for errors
2. Review the [Next.js documentation](https://nextjs.org/docs)
3. Search for issues on GitHub
4. Contact the developers

---

## Credits

Built with ❤️ using:

- [Next.js](https://nextjs.org/) - React framework
- [Tailwind CSS](https://tailwindcss.com/) - Styling
- [Framer Motion](https://www.framer.com/motion/) - Animations
- [Mermaid.js](https://mermaid.js.org/) - Diagrams
- [Monaco Editor](https://microsoft.github.io/monaco-editor/) - Code editing
- [Lucide Icons](https://lucide.dev/) - Icons

---

Happy coding! 🚀
