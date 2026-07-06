import type { FastifyInstance } from 'fastify';
import { z } from 'zod';
import type { VaultService } from '../services/vault.js';
import type { SettingsService } from '../services/settings.js';
import { ragSearch, ragContextForChat, formatRagContext } from '../services/rag.js';
import { setPersonaApiUrl } from '../services/persona.js';

export async function brainRoutes(
  app: FastifyInstance,
  vault: VaultService,
  settings: SettingsService
) {
  app.get('/api/brain/config', async () => settings.getBrainConfig());

  app.post('/api/brain/config', async (req) => {
    const body = z
      .object({
        captureMode: z.enum(['every_turn', 'manual', 'session_end', 'starred']).optional(),
        captureEnabled: z.boolean().optional(),
        ragEnabled: z.boolean().optional(),
        ragMaxChunks: z.number().min(1).max(20).optional(),
        personaApiUrl: z.string().optional(),
        onCaptureWorkflowId: z.string().optional(),
      })
      .parse(req.body);
    const merged = settings.setBrainConfig(body);
    if (merged.personaApiUrl) {
      setPersonaApiUrl(merged.personaApiUrl);
    }
    return merged;
  });

  app.get('/api/brain/today', async () => {
    const today = new Date().toISOString().slice(0, 10);
    const chats = vault
      .listNotes()
      .filter((n) => n.path.startsWith('Persona/Chats/'))
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
      .slice(0, 7);
    const personas = vault.listNotes().filter((n) => n.path.startsWith('Personas/'));
    const todayChat = vault.getNote(`Persona/Chats/${today}.md`);
    const recent = vault
      .listNotes()
      .filter((n) => !n.path.startsWith('Persona/Sessions/'))
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
      .slice(0, 10);
    return {
      date: today,
      todayChatPath: todayChat ? `Persona/Chats/${today}.md` : null,
      todayExchangeCount: todayChat
        ? (todayChat.content.match(/^## /gm) || []).length
        : 0,
      recentChats: chats,
      personas,
      recentNotes: recent,
    };
  });

  app.get('/api/brain/rag', async (req) => {
    const q = String((req.query as { q?: string }).q ?? '');
    const limit = Number((req.query as { limit?: string }).limit ?? settings.getBrainConfig().ragMaxChunks);
    const chunks = ragSearch(vault, q, limit);
    return { query: q, chunks, context: formatRagContext(chunks) };
  });

  app.post('/api/brain/rag/inject', async (req) => {
    const body = z.object({ message: z.string(), maxChunks: z.number().optional() }).parse(req.body);
    const cfg = settings.getBrainConfig();
    if (!cfg.ragEnabled) {
      return { enabled: false, context: '', injectedMessage: body.message };
    }
    const context = ragContextForChat(vault, body.message, body.maxChunks ?? cfg.ragMaxChunks);
    const injectedMessage = context ? `${context}${body.message}` : body.message;
    return { enabled: true, context, injectedMessage };
  });

  app.post('/api/brain/workspace-capture', async (req) => {
    const body = z.object({ workspaceId: z.string(), enabled: z.boolean() }).parse(req.body);
    settings.set(`capture_off_${body.workspaceId}`, body.enabled ? '0' : '1');
    return { ok: true, workspaceId: body.workspaceId, captureEnabled: body.enabled };
  });
}
