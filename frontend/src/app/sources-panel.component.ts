import { Component, input } from '@angular/core';
import { Source } from './models';

@Component({
    selector: 'app-sources-panel',
    standalone: true,
    template: `
    <aside class="sources">
      <h2>Sources</h2>
      @if (sources().length === 0) {
        <p class="muted">Cliquez sur une citation [1], [2]… pour voir la source correspondante.</p>
      }
      @for (s of sources(); track s.id) {
        <article class="source" [class.active]="s.id === active()" [class.uncited]="!cited().includes(s.id)">
          <header>
            <span class="badge">[{{ s.id }}]</span>
            <strong>{{ s.reference }}</strong>
            <span class="score" title="Similarité cosinus">{{ s.score.toFixed(3) }}</span>
          </header>
          <p class="meta">
            {{ s.file }} · page {{ s.page }} · {{ s.date }}
          </p>
          <p class="section">{{ s.section }}</p>
          <p class="excerpt">{{ s.excerpt }}</p>
          @if (!cited().includes(s.id)) {
            <p class="muted small">Fragment fourni au modèle, non cité dans la réponse.</p>
          }
        </article>
      }
    </aside>
  `,
})
export class SourcesPanelComponent {
    readonly sources = input.required<Source[]>();
    readonly cited = input<number[]>([]);
    readonly active = input<number | null>(null);
}