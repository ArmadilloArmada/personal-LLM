/**
 * Big Brain MCP server (stdio).
 * Tools: vault_search, vault_read, vault_capture_status, brain_config
 *
 * Run: npm run mcp --prefix big-brain/server
 */
import { createInterface } from 'node:readline';
import { getDb, ensureVault } from '../db.js';
import { VaultService } from '../services/vault.js';
import { SettingsService } from '../services/settings.js';
import { ragSearch } from '../services/rag.js';

ensureVault();
const db = getDb();
const vault = new VaultService(db);
const settings = new SettingsService(db);

const tools = [
  {
    name: 'vault_search',
    description: 'Search Big Brain vault notes by keyword',
    inputSchema: {
      type: 'object',
      properties: { query: { type: 'string' }, limit: { type: 'number' } },
      required: ['query'],
    },
  },
  {
    name: 'vault_read',
    description: 'Read a vault note by path',
    inputSchema: {
      type: 'object',
      properties: { path: { type: 'string' } },
      required: ['path'],
    },
  },
  {
    name: 'brain_config',
    description: 'Get Big Brain capture and RAG configuration',
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'vault_list_chats',
    description: 'List captured Persona chat daily notes',
    inputSchema: { type: 'object', properties: {} },
  },
];

function send(msg: unknown) {
  process.stdout.write(JSON.stringify(msg) + '\n');
}

function handleTool(name: string, args: Record<string, unknown>) {
  switch (name) {
    case 'vault_search': {
      const query = String(args.query ?? '');
      const limit = Number(args.limit ?? 5);
      return { chunks: ragSearch(vault, query, limit) };
    }
    case 'vault_read': {
      const notePath = String(args.path ?? '');
      const note = vault.getNote(notePath);
      if (!note) return { error: 'Note not found' };
      return { path: note.path, title: note.title, content: note.content, tags: note.tags };
    }
    case 'brain_config':
      return settings.getBrainConfig();
    case 'vault_list_chats':
      return {
        chats: vault.listNotes().filter((n: { path: string }) => n.path.startsWith('Persona/Chats/')),
      };
    default:
      return { error: `Unknown tool: ${name}` };
  }
}

const rl = createInterface({ input: process.stdin, output: process.stderr, terminal: false });

rl.on('line', (line) => {
  let req: { id?: number; method?: string; params?: Record<string, unknown> };
  try {
    req = JSON.parse(line);
  } catch {
    return;
  }

  const id = req.id ?? 0;

  if (req.method === 'initialize') {
    send({
      jsonrpc: '2.0',
      id,
      result: {
        protocolVersion: '2024-11-05',
        serverInfo: { name: 'big-brain', version: '1.0.1' },
        capabilities: { tools: {} },
      },
    });
    return;
  }

  if (req.method === 'tools/list') {
    send({ jsonrpc: '2.0', id, result: { tools } });
    return;
  }

  if (req.method === 'tools/call') {
    const params = req.params ?? {};
    const name = String(params.name ?? '');
    const args = (params.arguments ?? {}) as Record<string, unknown>;
    const result = handleTool(name, args);
    send({
      jsonrpc: '2.0',
      id,
      result: {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      },
    });
    return;
  }

  send({ jsonrpc: '2.0', id, error: { code: -32601, message: 'Method not found' } });
});

console.error('[Big Brain MCP] stdio server ready');
