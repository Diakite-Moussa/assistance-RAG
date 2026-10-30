import { Component, ElementRef, computed, inject, input, signal, viewChild } from '@angular/core';
import { finalize } from 'rxjs';
import { segmentAnswer } from './format';
import { ChatMessage } from './models';
import { RagApiService, describeError } from './rag-api.service';
import { SourcesPanelComponent } from './sources-panel.component';

const EXAMPLES = [
    'Quelle est la durée minimale d\'un PFE qui commence en février 2027 ?',
    'Combien de places de semestre d\'études à l\'étranger sont ouvertes au total ?',
    'Combien de jours avant le début d\'un stage la convention doit-elle être déposée ?',
    'Quel est le prix d\'un repas au restaurant de l\'École ?',
];

@Component({
    selector: 'app-chat',
    standalone: true,
    imports: [SourcesPanelComponent],
    template: `
    <div class="chat-layout">
      <section class="chat">
        <div class="messages" #scroller>
          @if (messages().length === 0) {
            <div class="hint">
              <p>Posez une question sur le règlement, les stages, la mobilité, le calendrier ou la vie étudiante.</p>
              <div class="chips">
                @for (e of examples; track e) {
                  <button type="button" class="chip" (click)="send(e)" [disabled]="loading()">{{ e }}</button>
                }
              </div>
            </div>
          }
          @for (m of messages(); track $index) {
            <article
              class="msg"
              [class.user]="m.role === 'user'"
              [class.error]="m.role === 'error'"
              [class.refusal]="m.response && !m.response.found"
            >
              @if (m.role === 'user') {
                <p>{{ m.text }}</p>
              } @else if (m.role === 'error') {
                <p>⚠ {{ m.text }}</p>
              } @else {
                @if (m.response && !m.response.found) {
                  <p class="tag">Hors des documents de l'École</p>
                }
                <p class="answer">
                  @for (seg of segments(m.text); track $index) {
                    @if (seg.kind === 'cite') {
                      <button
                        type="button"
                        class="cite"
                        [class.invalid]="!isValid(m, seg.n!)"
                        [disabled]="!isValid(m, seg.n!)"
                        (click)="select(m, seg.n!)"
                      >{{ seg.value }}</button>
                    } @else if (seg.kind === 'bold') {
                      <strong>{{ seg.value }}</strong>
                    } @else {
                      <span class="t">{{ seg.value }}</span>
                    }
                  }
                </p>
                @if (m.response && m.response.invalid_citations.length) {
                  <p class="warn">Citation(s) invalide(s) ignorée(s) : {{ m.response.invalid_citations.join(', ') }}</p>
                }
                @if (m.response) {
                  <p class="muted small">{{ m.response.latency_ms }} ms · {{ m.response.sources.length }} source(s)</p>
                }
              }
            </article>
          }
          @if (loading()) {
            <article class="msg loading" aria-live="polite">
              <span class="dots"><i></i><i></i><i></i></span> Recherche dans les documents…
            </article>
          }
        </div>

        <form class="composer" (submit)="onSubmit($event)">
          <input
            type="text"
            name="question"
            placeholder="Votre question…"
            autocomplete="off"
            [value]="question()"
            (input)="onInput($event)"
            [disabled]="loading()"
          />
          <button type="submit" [disabled]="loading() || !question().trim()">
            {{ loading() ? 'Envoi…' : 'Envoyer' }}
          </button>
        </form>
      </section>

      <app-sources-panel [sources]="panelSources()" [cited]="panelCited()" [active]="activeSource()" />
    </div>
  `,
})
export class ChatComponent {
    private readonly api = inject(RagApiService);

    readonly topK = input(5);
    readonly docType = input<string | null>(null);

    readonly examples = EXAMPLES;
    readonly messages = signal<ChatMessage[]>([]);
    readonly question = signal('');
    readonly loading = signal(false);
    readonly selected = signal<ChatMessage | null>(null);
    readonly activeSource = signal<number | null>(null);

    private readonly scroller = viewChild<ElementRef<HTMLElement>>('scroller');

    readonly panelSources = computed(() => this.selected()?.response?.sources ?? []);
    readonly panelCited = computed(() => {
        const r = this.selected()?.response;
        return r ? this.citedIn(r.answer) : [];
    });

    segments = segmentAnswer;

    onInput(e: Event): void {
        this.question.set((e.target as HTMLInputElement).value);
    }

    onSubmit(e: Event): void {
        e.preventDefault();
        this.send(this.question());
    }

    send(text: string): void {
        const q = text.trim();
        if (!q || this.loading()) return;
        this.messages.update((m) => [...m, { role: 'user', text: q }]);
        this.question.set('');
        this.loading.set(true);
        this.scrollDown();

        this.api
            .ask(q, this.topK(), this.docType())
            .pipe(finalize(() => { this.loading.set(false); this.scrollDown(); }))
            .subscribe({
                next: (r) => {
                    const msg: ChatMessage = { role: 'assistant', text: r.answer, response: r };
                    this.messages.update((m) => [...m, msg]);
                    this.selected.set(msg);
                    this.activeSource.set(null);
                },
                error: (err) => this.messages.update((m) => [...m, { role: 'error', text: describeError(err) }]),
            });
    }

    isValid(m: ChatMessage, n: number): boolean {
        return !!m.response?.sources.some((s) => s.id === n);
    }

    select(m: ChatMessage, n: number): void {
        this.selected.set(m);
        this.activeSource.set(n);
    }

    private citedIn(answer: string): number[] {
        return segmentAnswer(answer).filter((s) => s.kind === 'cite').map((s) => s.n!);
    }

    private scrollDown(): void {
        setTimeout(() => {
            const el = this.scroller()?.nativeElement;
            if (el) el.scrollTop = el.scrollHeight;
        });
    }
}