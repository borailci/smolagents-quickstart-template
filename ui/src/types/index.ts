// TypeScript interfaces for the Tutorial Generator UI

export interface TutorialFile {
    path: string;
    title: string;
}

export interface Codebase {
    id: string;
    name: string;
    description: string;
    icon: string;
    color: string;
    files: TutorialFile[];
}

export interface ContentConfig {
    codebases: Codebase[];
}
