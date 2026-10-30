export interface Filters {
    type: string | null;
}

export interface Source {
    id: number;
    chunk_id: string;
    file: string;
    reference: string;
    date: string;
    page: number;
    section: string;
    excerpt: string;
    score: number;
}

export interface AskResponse {
    answer: string;
    found: boolean;
    sources: Source[];
    invalid_citations: number[];
    latency_ms: number;
}

export interface SearchHit {
    chunk_id: string;
    file: string;
    reference: string;
    type: string;
    date: string;
    page: number;
    section: string;
    content: string;
    score: number;
}

export interface SearchResponse {
    hits: SearchHit[];
}

export interface DocumentInfo {
    file: string;
    title: string;
    reference: string;
    type: string;
    date: string;
    version: string;
    status: string;
    amends: string;
    chunks: number;
}

export interface HealthResponse {
    status: string;
    strategy: string;
    chunks: number;
}

export interface ChatMessage {
    role: 'user' | 'assistant' | 'error';
    text: string;
    response?: AskResponse;
}