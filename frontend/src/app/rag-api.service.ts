import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../environments/environment';
import { AskResponse, DocumentInfo, HealthResponse, SearchResponse } from './models';

@Injectable({ providedIn: 'root' })
export class RagApiService {
    private readonly http = inject(HttpClient);
    private readonly base = environment.apiUrl;

    health(): Observable<HealthResponse> {
        return this.http.get<HealthResponse>(`${this.base}/health`);
    }

    documents(): Observable<DocumentInfo[]> {
        return this.http.get<DocumentInfo[]>(`${this.base}/documents`);
    }

    search(question: string, topK: number, type: string | null): Observable<SearchResponse> {
        return this.http.post<SearchResponse>(`${this.base}/search`, {
            question,
            top_k: topK,
            filters: { type },
        });
    }

    ask(question: string, topK: number, type: string | null): Observable<AskResponse> {
        return this.http.post<AskResponse>(`${this.base}/ask`, {
            question,
            top_k: topK,
            filters: { type },
        });
    }
}

/** Transforme une erreur HTTP en message clair pour l'utilisateur. */
export function describeError(err: unknown): string {
    if (!(err instanceof HttpErrorResponse)) {
        return 'Une erreur inattendue est survenue.';
    }
    switch (err.status) {
        case 0:
            return "Impossible de joindre l'API. Vérifiez que le serveur est lancé.";
        case 422: {
            const detail = err.error?.detail;
            const msg = Array.isArray(detail) ? detail[0]?.msg : undefined;
            const clean = typeof msg === 'string' ? msg.replace(/^Value error, /, '') : null;
            return `Requête invalide (422)${clean ? ' : ' + clean : '.'}`;
        }
        case 502:
            return 'Le modèle de langage ne répond pas (502). Réessayez dans un instant.';
        case 503:
            return 'La base de connaissances est indisponible (503). Réessayez plus tard.';
        default:
            return `Erreur du serveur (${err.status}).`;
    }
}