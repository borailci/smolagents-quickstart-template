import yaml from 'js-yaml';
import { ContentConfig } from '@/types';

let cachedConfig: ContentConfig | null = null;

export async function loadContentConfig(): Promise<ContentConfig> {
    if (cachedConfig) return cachedConfig;

    try {
        const response = await fetch('/content.yaml');
        const text = await response.text();
        cachedConfig = yaml.load(text) as ContentConfig;
        return cachedConfig;
    } catch (error) {
        console.error('Failed to load content.yaml:', error);
        return { codebases: [] };
    }
}

export function getCodebaseById(config: ContentConfig, id: string) {
    return config.codebases.find(cb => cb.id === id);
}
