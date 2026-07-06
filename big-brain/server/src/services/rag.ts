import type { VaultService } from './vault.js';

export interface RagChunk {
  path: string;
  title: string;
  snippet: string;
  score: number;
}

export function ragSearch(vault: VaultService, query: string, limit = 5): RagChunk[] {
  const q = query.toLowerCase().trim();
  if (!q) return [];

  const results: RagChunk[] = [];
  for (const meta of vault.listNotes()) {
    const note = vault.getNote(meta.path);
    if (!note) continue;
    const haystack = `${note.title} ${note.content} ${note.tags.join(' ')}`.toLowerCase();
    if (!haystack.includes(q)) continue;

    const idx = haystack.indexOf(q);
    const start = Math.max(0, idx - 80);
    const end = Math.min(note.content.length, idx + 120);
    const snippet = note.content.slice(start, end).replace(/\n/g, ' ').trim();

    results.push({
      path: note.path,
      title: note.title,
      snippet: snippet || note.title,
      score: (note.content.match(new RegExp(q, 'gi')) || []).length + (note.title.toLowerCase().includes(q) ? 2 : 0),
    });
  }

  return results.sort((a, b) => b.score - a.score).slice(0, limit);
}

export function formatRagContext(chunks: RagChunk[]): string {
  if (!chunks.length) return '';
  const lines = chunks.map(
    (c, i) => `[${i + 1}] ${c.title} (${c.path})\n${c.snippet}`
  );
  return `Relevant notes from Big Brain:\n\n${lines.join('\n\n')}\n\n---\n\n`;
}

export function ragContextForChat(vault: VaultService, userMessage: string, maxChunks = 5): string {
  const words = userMessage.split(/\s+/).filter((w) => w.length > 3).slice(0, 8);
  const query = words.join(' ') || userMessage.slice(0, 100);
  const chunks = ragSearch(vault, query, maxChunks);
  return formatRagContext(chunks);
}
