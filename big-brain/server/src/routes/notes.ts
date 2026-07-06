import type { FastifyInstance } from 'fastify';
import { z } from 'zod';
import type { VaultService } from '../services/vault.js';

function decodePath(encoded: string): string {
  return decodeURIComponent(encoded);
}

export async function notesRoutes(app: FastifyInstance, vault: VaultService) {
  app.get('/api/notes', async () => vault.listNotes());

  app.get<{ Params: { notePath: string } }>(
    '/api/notes/:notePath',
    async (req, reply) => {
      const notePath = decodePath(req.params.notePath);
      const note = vault.getNote(notePath);
      if (!note) return reply.status(404).send({ error: 'Note not found' });
      return note;
    }
  );

  app.post('/api/notes', async (req, reply) => {
    const body = z.object({ path: z.string(), content: z.string().optional() }).parse(req.body);
    try {
      return vault.createNote(body.path, body.content);
    } catch (err) {
      return reply.status(409).send({ error: err instanceof Error ? err.message : 'Conflict' });
    }
  });

  app.put<{ Params: { notePath: string } }>(
    '/api/notes/:notePath',
    async (req, reply) => {
      const notePath = decodePath(req.params.notePath);
      const body = z
        .object({ content: z.string(), title: z.string().optional() })
        .parse(req.body);
      const existing = vault.getNote(notePath);
      if (!existing) return reply.status(404).send({ error: 'Note not found' });
      return vault.saveNote(notePath, body.content, body.title);
    }
  );

  app.delete<{ Params: { notePath: string } }>(
    '/api/notes/:notePath',
    async (req, reply) => {
      const notePath = decodePath(req.params.notePath);
      const existing = vault.getNote(notePath);
      if (!existing) return reply.status(404).send({ error: 'Note not found' });
      vault.deleteNote(notePath);
      return { ok: true };
    }
  );

  app.get('/api/search', async (req) => {
    const q = String((req.query as { q?: string }).q ?? '');
    if (!q.trim()) return [];
    return vault.search(q);
  });

  app.get('/api/graph', async () => vault.getGraph());
}
