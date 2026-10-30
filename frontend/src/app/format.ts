export interface Segment {
    kind: 'text' | 'bold' | 'cite';
    value: string;
    n?: number;
}

/** Découpe une réponse en texte, gras (**…**) et citations ([1], [2, 3]) sans utiliser innerHTML. */
export function segmentAnswer(text: string): Segment[] {
    const out: Segment[] = [];
    const re = /(\*\*[^*]+\*\*|\[\d+(?:\s*[,;]\s*\d+)*\])/g;
    let last = 0;
    for (const m of text.matchAll(re)) {
        const idx = m.index ?? 0;
        if (idx > last) out.push({ kind: 'text', value: text.slice(last, idx) });
        const token = m[0];
        if (token.startsWith('**')) {
            out.push({ kind: 'bold', value: token.slice(2, -2) });
        } else {
            for (const n of token.match(/\d+/g) ?? []) {
                out.push({ kind: 'cite', value: `[${n}]`, n: Number(n) });
            }
        }
        last = idx + token.length;
    }
    if (last < text.length) out.push({ kind: 'text', value: text.slice(last) });
    return out;
}