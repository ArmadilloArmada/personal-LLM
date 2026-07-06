import crypto from 'node:crypto';
import type Database from 'better-sqlite3';
import type { VaultService } from './vault.js';
import type { NoteDetail } from './vault.js';
import type {
  ExecutionContext,
  WorkflowDefinition,
  WorkflowPublic,
  WorkflowRecord,
} from '../workflow/types.js';
import { runNode } from '../workflow/nodes/index.js';
import { SEED_WORKFLOWS } from '../workflow/seed.js';

export class WorkflowEngine {
  constructor(
    private db: Database.Database,
    private vault: VaultService
  ) {}

  listWorkflows(): WorkflowPublic[] {
    return this.db
      .prepare(
        'SELECT id, name, description, icon, definition FROM workflows ORDER BY name'
      )
      .all()
      .map((row) => this.rowToPublic(row as Record<string, unknown>));
  }

  getWorkflow(id: string): WorkflowRecord | null {
    const row = this.db.prepare('SELECT * FROM workflows WHERE id = ?').get(id) as
      | Record<string, unknown>
      | undefined;
    if (!row) return null;
    return this.rowToRecord(row);
  }

  upsertWorkflow(data: {
    id: string;
    name: string;
    description?: string;
    icon?: string;
    definition: WorkflowDefinition;
  }): WorkflowPublic {
    const definitionJson = JSON.stringify(data.definition);
    this.db
      .prepare(
        `INSERT INTO workflows (id, name, description, icon, definition)
         VALUES (?, ?, ?, ?, ?)
         ON CONFLICT(id) DO UPDATE SET
           name=excluded.name,
           description=excluded.description,
           icon=excluded.icon,
           definition=excluded.definition`
      )
      .run(
        data.id,
        data.name,
        data.description ?? '',
        data.icon ?? '⚡',
        definitionJson
      );
    return this.getWorkflow(data.id)!;
  }

  deleteWorkflow(id: string): void {
    this.db.prepare('DELETE FROM workflows WHERE id = ?').run(id);
  }

  seedWorkflows(): void {
    for (const wf of SEED_WORKFLOWS) {
      const existing = this.getWorkflow(wf.id);
      if (!existing) {
        this.upsertWorkflow(wf);
      }
    }
  }

  async triggerWorkflow(
    workflowId: string,
    note: NoteDetail | null
  ): Promise<{ executionId: string; status: string; response: unknown }> {
    const workflow = this.getWorkflow(workflowId);
    if (!workflow) throw new Error('Workflow not found');

    const executionId = crypto.randomUUID();
    const started = Date.now();
    const ctx: ExecutionContext = {
      note: note
        ? {
            path: note.path,
            title: note.title,
            content: note.content,
            tags: note.tags,
            wikilinks: note.wikilinks,
            frontmatter: note.frontmatter,
          }
        : null,
      llm: { output: '' },
      rag: { context: '', chunks: [] },
      transform: { output: null },
      branch: { result: false },
      output: { value: null },
    };

    const nodeLogs: Array<{ nodeId: string; type: string; ok: boolean; error?: string }> = [];

    try {
      const order = topologicalOrder(workflow.definition);
      const nodeMap = new Map(workflow.definition.nodes.map((n) => [n.id, n]));

      for (const nodeId of order) {
        const node = nodeMap.get(nodeId);
        if (!node) continue;
        if (node.type === 'noteTrigger' || node.type === 'captureTrigger') continue;
        if (!shouldRunNode(nodeId, workflow.definition, ctx)) continue;
        try {
          await runNode(node.type, node.data, ctx, this.vault);
          nodeLogs.push({ nodeId, type: node.type, ok: true });
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          nodeLogs.push({ nodeId, type: node.type, ok: false, error: message });
          throw err;
        }
      }

      const response = {
        output: ctx.output.value ?? ctx.llm.output ?? ctx.transform.output,
        llm: ctx.llm.output,
        transform: ctx.transform.output,
        nodeLogs,
      };
      this.recordExecution(executionId, workflowId, note?.path ?? null, 'success', response, Date.now() - started);
      return { executionId, status: 'success', response };
    } catch (err) {
      const response = {
        error: err instanceof Error ? err.message : String(err),
        nodeLogs,
        partial: { llm: ctx.llm.output, transform: ctx.transform.output },
      };
      this.recordExecution(executionId, workflowId, note?.path ?? null, 'error', response, Date.now() - started);
      throw err;
    }
  }

  recordExecution(
    id: string,
    workflowId: string,
    notePath: string | null,
    status: string,
    response: unknown,
    durationMs: number
  ): void {
    this.db
      .prepare(
        `INSERT INTO executions (id, workflow_id, note_path, status, response, created_at, duration_ms)
         VALUES (?, ?, ?, ?, ?, ?, ?)`
      )
      .run(
        id,
        workflowId,
        notePath,
        status,
        JSON.stringify(response),
        new Date().toISOString(),
        durationMs
      );
  }

  listExecutions(limit = 50) {
    return this.db
      .prepare(
        `SELECT e.id, e.workflow_id as workflowId, e.note_path as notePath,
                e.status, e.response, e.created_at as createdAt,
                e.duration_ms as durationMs, w.name as workflowName
         FROM executions e
         LEFT JOIN workflows w ON w.id = e.workflow_id
         ORDER BY e.created_at DESC
         LIMIT ?`
      )
      .all(limit)
      .map((row) => {
        const r = row as Record<string, unknown>;
        return {
          ...r,
          response: r.response ? JSON.parse(r.response as string) : null,
        };
      });
  }

  async triggerOnCapture(capture: {
    personaId: string;
    personaName: string;
    userMessage: string;
    assistantMessage: string;
    dailyNotePath: string;
    personaNotePath: string;
  }): Promise<void> {
    const workflows = this.listWorkflows().filter((wf) =>
      wf.definition.nodes.some((n) => n.type === 'captureTrigger')
    );
    const note = this.vault.getNote(capture.dailyNotePath);
    for (const wf of workflows) {
      const executionId = crypto.randomUUID();
      const started = Date.now();
      const ctx: ExecutionContext = {
        note: note
          ? {
              path: note.path,
              title: note.title,
              content: note.content,
              tags: note.tags,
              wikilinks: note.wikilinks,
              frontmatter: note.frontmatter,
            }
          : null,
        capture,
        llm: { output: '' },
        rag: { context: '', chunks: [] },
        transform: { output: null },
        branch: { result: false },
        output: { value: null },
      };
      try {
        const order = topologicalOrder(wf.definition);
        const nodeMap = new Map(wf.definition.nodes.map((n) => [n.id, n]));
        for (const nodeId of order) {
          const node = nodeMap.get(nodeId);
          if (!node || node.type === 'captureTrigger' || node.type === 'noteTrigger') continue;
          if (!shouldRunNode(nodeId, wf.definition, ctx)) continue;
          await runNode(node.type, node.data, ctx, this.vault);
        }
        const response = { output: ctx.output.value ?? ctx.llm.output, capture: true };
        this.recordExecution(executionId, wf.id, note?.path ?? null, 'success', response, Date.now() - started);
      } catch (err) {
        const response = { error: err instanceof Error ? err.message : String(err), capture: true };
        this.recordExecution(executionId, wf.id, note?.path ?? null, 'error', response, Date.now() - started);
      }
    }
  }

  private rowToRecord(row: Record<string, unknown>): WorkflowRecord {
    return {
      id: row.id as string,
      name: row.name as string,
      description: row.description as string,
      icon: row.icon as string,
      definition: JSON.parse(row.definition as string) as WorkflowDefinition,
    };
  }

  private rowToPublic(row: Record<string, unknown>): WorkflowPublic {
    return this.rowToRecord(row);
  }
}

function shouldRunNode(
  nodeId: string,
  definition: WorkflowDefinition,
  ctx: ExecutionContext
): boolean {
  const incoming = definition.edges.filter((e) => e.target === nodeId);
  for (const e of incoming) {
    const source = definition.nodes.find((n) => n.id === e.source);
    if (source?.type === 'branch' && e.when) {
      const want = e.when === 'true';
      if (ctx.branch.result !== want) return false;
    }
  }
  return true;
}

function topologicalOrder(definition: WorkflowDefinition): string[] {
  const nodes = definition.nodes;
  const edges = definition.edges;
  const trigger = nodes.find((n) => n.type === 'noteTrigger' || n.type === 'captureTrigger');
  if (!trigger) throw new Error('Workflow missing trigger node');

  const adj = new Map<string, string[]>();
  for (const e of edges) {
    if (!adj.has(e.source)) adj.set(e.source, []);
    adj.get(e.source)!.push(e.target);
  }

  const visited = new Set<string>();
  const order: string[] = [];

  function dfs(id: string) {
    if (visited.has(id)) return;
    visited.add(id);
    order.push(id);
    for (const next of adj.get(id) ?? []) dfs(next);
  }

  dfs(trigger.id);

  for (const n of nodes) {
    if (!visited.has(n.id)) order.push(n.id);
  }

  return order;
}
