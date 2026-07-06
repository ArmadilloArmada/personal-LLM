import vm from 'node:vm';
import type { ExecutionContext } from '../types.js';
import type { VaultService } from '../../services/vault.js';
import { personaChat } from '../../services/persona.js';
import { renderTemplate } from '../../lib/template.js';
import { ragContextForChat, ragSearch } from '../../services/rag.js';

const TRANSFORM_TIMEOUT = Number(process.env.WORKFLOW_TRANSFORM_TIMEOUT_MS ?? 5000);

export async function runNode(
  type: string,
  data: Record<string, unknown>,
  ctx: ExecutionContext,
  vault: VaultService
): Promise<void> {
  switch (type) {
    case 'noteTrigger':
    case 'captureTrigger':
      return;
    case 'llm':
      await runLlmNode(data, ctx, vault);
      return;
    case 'personaRag':
      runPersonaRagNode(data, ctx, vault);
      return;
    case 'transform':
      runTransformNode(data, ctx);
      return;
    case 'branch':
      runBranchNode(data, ctx);
      return;
    case 'vaultWrite':
      await runVaultWriteNode(data, ctx, vault);
      return;
    case 'output':
      ctx.output.value = data.valueTemplate
        ? renderTemplate(String(data.valueTemplate), ctx as unknown as Record<string, unknown>)
        : ctx.llm.output || ctx.transform.output;
      return;
    default:
      throw new Error(`Unknown node type: ${type}`);
  }
}

function runPersonaRagNode(
  data: Record<string, unknown>,
  ctx: ExecutionContext,
  vault: VaultService
): void {
  const queryTemplate = String(data.queryTemplate ?? '{{note.content}}');
  const query = renderTemplate(queryTemplate, ctx as unknown as Record<string, unknown>);
  const maxChunks = Number(data.maxChunks ?? 5);
  const chunks = ragSearch(vault, query, maxChunks);
  ctx.rag.chunks = chunks;
  ctx.rag.context = chunks.length
    ? `Relevant vault notes:\n${chunks.map((c) => `- ${c.title}: ${c.snippet}`).join('\n')}`
    : '';
}

async function runLlmNode(
  data: Record<string, unknown>,
  ctx: ExecutionContext,
  vault: VaultService
): Promise<void> {
  const personaId = String(data.personaId ?? process.env.PERSONA_DEFAULT_PERSONA_ID ?? 'byte');
  const workspaceId = String(data.workspaceId ?? 'default');
  const useRag = Boolean(data.useRag);
  const systemPrompt = data.systemPrompt
    ? renderTemplate(String(data.systemPrompt), ctx as unknown as Record<string, unknown>)
    : '';
  let userMessage = renderTemplate(
    String(data.messageTemplate ?? data.userTemplate ?? '{{note.content}}'),
    ctx as unknown as Record<string, unknown>
  );
  if (useRag && !ctx.rag.context) {
    const ragCtx = ragContextForChat(vault, userMessage, Number(data.maxChunks ?? 5));
    ctx.rag.context = ragCtx;
  }
  if (ctx.rag.context) {
    userMessage = `${ctx.rag.context}\n\n${userMessage}`;
  }
  const message = systemPrompt ? `${systemPrompt}\n\n${userMessage}` : userMessage;
  ctx.llm.output = await personaChat({ message, personaId, workspaceId });
}
function runBranchNode(data: Record<string, unknown>, ctx: ExecutionContext): void {
  const code = String(data.condition ?? 'return true;');
  const sandbox = {
    note: ctx.note,
    capture: ctx.capture,
    llm: ctx.llm,
    rag: ctx.rag,
    transform: ctx.transform,
    JSON,
    Boolean,
    String,
  };
  const script = new vm.Script(`result = (function() { ${code} })();`);
  script.runInNewContext(sandbox, { timeout: TRANSFORM_TIMEOUT, displayErrors: true });
  ctx.branch.result = Boolean((sandbox as { result?: unknown }).result);
}

function runTransformNode(data: Record<string, unknown>, ctx: ExecutionContext): void {
  const code = String(data.code ?? '');
  const sandbox = {
    note: ctx.note,
    capture: ctx.capture,
    llm: ctx.llm,
    rag: ctx.rag,
    transform: ctx.transform,
    output: null as unknown,
    JSON,
    String,
    Array,
    Object,
    RegExp,
  };
  const script = new vm.Script(`output = (function() { ${code} })();`);
  script.runInNewContext(sandbox, { timeout: TRANSFORM_TIMEOUT, displayErrors: true });
  ctx.transform.output = sandbox.output;
}

async function runVaultWriteNode(
  data: Record<string, unknown>,
  ctx: ExecutionContext,
  vault: VaultService
): Promise<void> {
  const action = String(data.action ?? 'append');
  const notePath = renderTemplate(
    String(data.notePathTemplate ?? '{{note.path}}'),
    ctx as unknown as Record<string, unknown>
  );
  const content = renderTemplate(
    String(data.contentTemplate ?? ''),
    ctx as unknown as Record<string, unknown>
  );

  switch (action) {
    case 'append':
      vault.appendToNote(notePath, content);
      break;
    case 'create':
      vault.createNote(notePath, content);
      break;
    case 'update_frontmatter': {
      const fm = data.frontmatter as Record<string, unknown> | undefined;
      if (fm) vault.updateFrontmatter(notePath, fm);
      break;
    }
    default:
      throw new Error(`Unknown vaultWrite action: ${action}`);
  }
}
