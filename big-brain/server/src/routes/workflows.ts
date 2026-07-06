import type { FastifyInstance } from 'fastify';
import { z } from 'zod';
import type { WorkflowDefinition } from '../workflow/types.js';
import type { WorkflowEngine } from '../services/workflow-engine.js';
import type { VaultService } from '../services/vault.js';
import { listPersonas, personaHealthCheck, getPersonaApiUrl } from '../services/persona.js';

const workflowDefinitionSchema = z.object({
  nodes: z.array(
    z.object({
      id: z.string(),
      type: z.string(),
      position: z.object({ x: z.number(), y: z.number() }),
      data: z.record(z.unknown()),
    })
  ),
  edges: z.array(
    z.object({
      id: z.string(),
      source: z.string(),
      target: z.string(),
      when: z.enum(['true', 'false']).optional(),
    })
  ),
});

export async function workflowRoutes(
  app: FastifyInstance,
  engine: WorkflowEngine,
  vault: VaultService
) {
  app.get('/api/workflows', async () => engine.listWorkflows());

  app.get('/api/workflows/:id', async (req, reply) => {
    const { id } = req.params as { id: string };
    const wf = engine.getWorkflow(id);
    if (!wf) return reply.status(404).send({ error: 'Workflow not found' });
    return wf;
  });

  app.post('/api/workflows', async (req, reply) => {
    const body = z
      .object({
        id: z.string().min(1),
        name: z.string().min(1),
        description: z.string().optional(),
        icon: z.string().optional(),
        definition: workflowDefinitionSchema,
      })
      .parse(req.body);
    try {
      return engine.upsertWorkflow({
        ...body,
        definition: body.definition as WorkflowDefinition,
      });
    } catch (err) {
      return reply.status(400).send({ error: err instanceof Error ? err.message : 'Bad request' });
    }
  });

  app.delete('/api/workflows/:id', async (req, reply) => {
    const { id } = req.params as { id: string };
    const wf = engine.getWorkflow(id);
    if (!wf) return reply.status(404).send({ error: 'Workflow not found' });
    engine.deleteWorkflow(id);
    return { ok: true };
  });

  app.post('/api/workflows/:id/trigger', async (req, reply) => {
    const { id } = req.params as { id: string };
    const body = z.object({ notePath: z.string().optional() }).parse(req.body ?? {});
    let note = null;
    if (body.notePath) {
      note = vault.getNote(body.notePath);
      if (!note) return reply.status(404).send({ error: 'Note not found' });
    }
    try {
      return await engine.triggerWorkflow(id, note);
    } catch (err) {
      return reply.status(502).send({
        error: err instanceof Error ? err.message : 'Trigger failed',
      });
    }
  });

  app.get('/api/executions', async () => engine.listExecutions());

  app.get('/api/persona/status', async () => {
    const health = await personaHealthCheck();
    return { url: getPersonaApiUrl(), ...health };
  });

  app.get('/api/persona/personas', async () => {
    const personas = await listPersonas();
    return { personas };
  });
}
