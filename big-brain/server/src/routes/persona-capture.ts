import type { FastifyInstance } from 'fastify';
import { z } from 'zod';
import type { VaultService } from '../services/vault.js';
import type { SettingsService } from '../services/settings.js';
import type { WorkflowEngine } from '../services/workflow-engine.js';

const CAPTURE_SECRET = process.env.BIG_BRAIN_CAPTURE_SECRET ?? '';

export async function personaCaptureRoutes(
  app: FastifyInstance,
  vault: VaultService,
  settings: SettingsService,
  engine: WorkflowEngine
) {
  app.post('/api/persona/capture', async (req, reply) => {
    if (CAPTURE_SECRET) {
      const auth = req.headers['x-big-brain-secret'];
      if (auth !== CAPTURE_SECRET) {
        return reply.status(401).send({ error: 'Unauthorized' });
      }
    }

    const body = z
      .object({
        personaId: z.string(),
        personaName: z.string().optional(),
        workspaceId: z.string().optional(),
        userMessage: z.string(),
        assistantMessage: z.string(),
        mode: z.string().optional(),
        sessionId: z.string().optional(),
        captureMode: z.enum(['every_turn', 'manual', 'session_end', 'starred']).optional(),
        starred: z.boolean().optional(),
        autoTitle: z.string().optional(),
        redact: z.boolean().optional(),
        force: z.boolean().optional(),
      })
      .parse(req.body);

    const cfg = settings.getBrainConfig();
    if (!settings.isCaptureEnabled(body.workspaceId)) {
      return { ok: false, skipped: true, reason: 'capture_disabled' };
    }

    const effectiveMode = body.captureMode ?? cfg.captureMode;
    if (!body.force) {
      if (effectiveMode === 'manual' && !body.starred) {
        return { ok: false, skipped: true, reason: 'manual_mode' };
      }
      if (effectiveMode === 'starred' && !body.starred) {
        return { ok: false, skipped: true, reason: 'starred_only' };
      }
      if (effectiveMode === 'session_end') {
        return { ok: false, skipped: true, reason: 'session_end_buffered' };
      }
    }

    try {
      const result = vault.capturePersonaChat({
        ...body,
        redact: body.redact ?? false,
        skipDedupe: body.force,
      });

      if (result.skipped) {
        return { ok: true, ...result };
      }

      engine.triggerOnCapture({
        personaId: body.personaId,
        personaName: body.personaName ?? body.personaId,
        userMessage: body.userMessage,
        assistantMessage: body.assistantMessage,
        dailyNotePath: result.dailyNotePath,
        personaNotePath: result.personaNotePath,
      }).catch((err) => {
        req.log.warn({ err }, 'on-capture workflow failed');
      });

      const onCaptureId = cfg.onCaptureWorkflowId;
      if (onCaptureId) {
        const note = vault.getNote(result.dailyNotePath);
        if (note) {
          engine.triggerWorkflow(onCaptureId, note).catch((err) => {
            req.log.warn({ err }, 'configured on-capture workflow failed');
          });
        }
      }

      return { ok: true, ...result };
    } catch (err) {
      return reply.status(400).send({
        error: err instanceof Error ? err.message : 'Capture failed',
      });
    }
  });

  app.post('/api/persona/capture/session-end', async (req, reply) => {
    const body = z
      .object({
        personaId: z.string(),
        personaName: z.string().optional(),
        sessionId: z.string(),
        turns: z.array(
          z.object({
            userMessage: z.string(),
            assistantMessage: z.string(),
            starred: z.boolean().optional(),
          })
        ),
      })
      .parse(req.body);

    const cfg = settings.getBrainConfig();
    if (cfg.captureMode !== 'session_end' && !body.turns.some((t) => t.starred)) {
      return { ok: false, skipped: true, reason: 'not_session_end_mode' };
    }

    const results = [];
    for (const turn of body.turns) {
      const r = vault.capturePersonaChat({
        personaId: body.personaId,
        personaName: body.personaName,
        sessionId: body.sessionId,
        userMessage: turn.userMessage,
        assistantMessage: turn.assistantMessage,
        starred: turn.starred,
        captureMode: 'session_end',
      });
      results.push(r);
    }

    try {
      vault.captureSessionSummary({
        personaId: body.personaId,
        personaName: body.personaName,
        sessionId: body.sessionId,
      });
    } catch {
      // session note may not exist if no turns
    }

    return { ok: true, captured: results.filter((r) => !r.skipped).length };
  });

  app.get('/api/persona/chats', async () => {
    const notes = vault.listNotes().filter((n) => n.path.startsWith('Persona/Chats/'));
    return { chats: notes };
  });

  app.get('/api/persona/sessions', async () => {
    const notes = vault.listNotes().filter((n) => n.path.startsWith('Persona/Sessions/'));
    return { sessions: notes };
  });

  app.delete('/api/persona/chats/:date', async (req, reply) => {
    const { date } = req.params as { date: string };
    const path = `Persona/Chats/${date}.md`;
    const note = vault.getNote(path);
    if (!note) return reply.status(404).send({ error: 'Chat note not found' });
    vault.deleteNote(path);
    return { ok: true };
  });
}
