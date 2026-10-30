import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ChatComponent } from './chat.component';
import { DocumentsComponent } from './documents.component';
import { DocumentInfo, HealthResponse } from './models';
import { RagApiService, describeError } from './rag-api.service';
import { SearchDebugComponent } from './search-debug.component';

type Tab = 'chat' | 'documents' | 'search';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [ChatComponent, DocumentsComponent, SearchDebugComponent],
  template: `
    <header class="topbar">
      <h1>Assistant Scolarité <small>École d'Ingénieurs Hélianthe</small></h1>
      <span class="health" [class.ok]="!!health()" [class.down]="!!healthError()">{{ healthLabel() }}</span>
    </header>

    <nav class="tabs">
      <button type="button" [class.on]="tab() === 'chat'" (click)="tab.set('chat')">Conversation</button>
      <button type="button" [class.on]="tab() === 'documents'" (click)="tab.set('documents')">Documents</button>
      <button type="button" [class.on]="tab() === 'search'" (click)="tab.set('search')">Recherche</button>
    </nav>

    <section class="controls">
      <label>
        Fragments (top_k)
        <input type="number" min="1" max="20" [value]="topK()" (input)="onTopK($event)" />
      </label>
      <label>
        Type de document
        <select (change)="onType($event)">
          <option value="">Tous</option>
          @for (t of types(); track t) {
            <option [value]="t">{{ t }}</option>
          }
        </select>
      </label>
    </section>

    <main>
      <div [hidden]="tab() !== 'chat'"><app-chat [topK]="topK()" [docType]="docType()" /></div>
      <div [hidden]="tab() !== 'documents'"><app-documents [documents]="documents()" [error]="docsError()" /></div>
      <div [hidden]="tab() !== 'search'"><app-search-debug [topK]="topK()" [docType]="docType()" /></div>
    </main>
  `,
})
export class App implements OnInit {
  private readonly api = inject(RagApiService);

  readonly tab = signal<Tab>('chat');
  readonly topK = signal(5);
  readonly docType = signal<string | null>(null);

  readonly health = signal<HealthResponse | null>(null);
  readonly healthError = signal<string | null>(null);
  readonly documents = signal<DocumentInfo[]>([]);
  readonly docsError = signal<string | null>(null);

  readonly types = computed(() => [...new Set(this.documents().map((d) => d.type))]);
  readonly healthLabel = computed(() => {
    const h = this.health();
    if (h) return `API connectée · ${h.chunks} fragments`;
    return this.healthError() ?? 'Connexion à l\'API…';
  });

  ngOnInit(): void {
    this.api.health().subscribe({
      next: (h) => this.health.set(h),
      error: (err) => this.healthError.set(describeError(err)),
    });
    this.api.documents().subscribe({
      next: (d) => this.documents.set(d),
      error: (err) => this.docsError.set(describeError(err)),
    });
  }

  onTopK(e: Event): void {
    const v = Math.round(Number((e.target as HTMLInputElement).value));
    this.topK.set(Number.isFinite(v) ? Math.min(20, Math.max(1, v)) : 5);
  }

  onType(e: Event): void {
    this.docType.set((e.target as HTMLSelectElement).value || null);
  }
}