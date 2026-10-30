import { Component, inject, input, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { SearchHit } from './models';
import { RagApiService, describeError } from './rag-api.service';

@Component({
    selector: 'app-search-debug',
    standalone: true,
    template: `
    <section class="debug">
      <h2>Recherche (mode débogage)</h2>
      <p class="muted">Fragments bruts et scores de similarité, sans appel au modèle de langage.</p>
      <form class="composer" (submit)="onSubmit($event)">
        <input
          type="text"
          name="q"
          placeholder="Question à tester…"
          [value]="question()"
          (input)="onInput($event)"
          [disabled]="loading()"
        />
        <button type="submit" [disabled]="loading() || !question().trim()">
          {{ loading() ? 'Recherche…' : 'Chercher' }}
        </button>
      </form>
      @if (error()) {
        <p class="msg error">⚠ {{ error() }}</p>
      }
      @for (h of hits(); track h.chunk_id; let i = $index) {
        <article class="hit">
          <header>
            <span class="badge">#{{ i + 1 }}</span>
            <strong>{{ h.reference }}</strong>
            <span class="score">{{ h.score.toFixed(4) }}</span>
          </header>
          <div class="bar"><span [style.width.%]="h.score * 100"></span></div>
          <p class="meta">{{ h.section }} · page {{ h.page }} · {{ h.type }} · {{ h.date }}</p>
          <pre>{{ h.content }}</pre>
        </article>
      }
    </section>
  `,
})
export class SearchDebugComponent {
    private readonly api = inject(RagApiService);

    readonly topK = input(5);
    readonly docType = input<string | null>(null);

    readonly question = signal('');
    readonly loading = signal(false);
    readonly error = signal<string | null>(null);
    readonly hits = signal<SearchHit[]>([]);

    onInput(e: Event): void {
        this.question.set((e.target as HTMLInputElement).value);
    }

    onSubmit(e: Event): void {
        e.preventDefault();
        const q = this.question().trim();
        if (!q || this.loading()) return;
        this.loading.set(true);
        this.error.set(null);
        this.api
            .search(q, this.topK(), this.docType())
            .pipe(finalize(() => this.loading.set(false)))
            .subscribe({
                next: (r) => this.hits.set(r.hits),
                error: (err) => { this.hits.set([]); this.error.set(describeError(err)); },
            });
    }
}