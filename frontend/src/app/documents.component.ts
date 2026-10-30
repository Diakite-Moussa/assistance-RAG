import { Component, input } from '@angular/core';
import { DocumentInfo } from './models';

@Component({
    selector: 'app-documents',
    standalone: true,
    template: `
    <section class="docs">
      <h2>Documents indexés ({{ documents().length }})</h2>
      @if (error()) {
        <p class="msg error">⚠ {{ error() }}</p>
      }
      <div class="doc-grid">
        @for (d of documents(); track d.reference) {
          <article class="doc">
            <header>
              <strong>{{ d.title }}</strong>
              <span class="badge">{{ d.chunks }} fragments</span>
            </header>
            <p class="meta">{{ d.reference }} · {{ d.type }}</p>
            <p class="meta">Publié le {{ d.date }} · version {{ d.version }}</p>
            <p class="small">{{ d.status }}</p>
            @if (d.amends) {
              <p class="tag">Modifie {{ d.amends }}</p>
            }
          </article>
        }
      </div>
    </section>
  `,
})
export class DocumentsComponent {
    readonly documents = input.required<DocumentInfo[]>();
    readonly error = input<string | null>(null);
}