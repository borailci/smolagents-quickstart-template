export interface TutorialFile {
    path: string;
    title: string;
}

export interface CodebaseConfig {
    id: string;
    name: string;
    description: string;
    icon: string;
    color: string;
    files: TutorialFile[];
}

export interface ContentConfig {
    codebases: CodebaseConfig[];
}
