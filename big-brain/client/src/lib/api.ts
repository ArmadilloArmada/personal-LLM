export interface NoteMeta {
  path: string;
  title: string;
  updatedAt: string;
}

export interface NoteDetail extends NoteMeta {
  content: string;
  frontmatter: Record<string, unknown>;
  tags: string[];
  wikilinks: string[];
  backlinks: string[];
}

export interface WorkflowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: Record<string, unknown>;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
}

export interface WorkflowDefinition {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  icon: string;
  definition: WorkflowDefinition;
}

export interface Execution {
  id: string;
  workflowId: string;
  workflowName?: string;
  notePath: string | null;
  status: string;
  response: unknown;
  createdAt: string;
  durationMs: number;
}

export interface GraphData {
  nodes: { id: string; title: string; kind?: string }[];
  links: { source: string; target: string }[];
}

export const GRAPH_COLORS: Record<string, string> = {
  persona: '#c084fc',
  chat: '#89b4fa',
  session: '#67e8f9',
  project: '#a6e3a1',
  note: '#6c7086',
};

export interface BrainConfig {
  captureMode: 'every_turn' | 'manual' | 'session_end' | 'starred';
  captureEnabled: boolean;
  ragEnabled: boolean;
  ragMaxChunks: number;
  personaApiUrl: string;
  onCaptureWorkflowId?: string;
}

export interface TodayData {
  date: string;
  todayChatPath: string | null;
  todayExchangeCount: number;
  recentChats: NoteMeta[];
  personas: NoteMeta[];
  recentNotes: NoteMeta[];
}

export interface RagResult {
  query: string;
  chunks: Array<{ path: string; title: string; snippet: string; score: number }>;
  context: string;
}

export interface PersonaInfo {
  id: string;
  name: string;
  role?: string;
}

const BASE = `${import.meta.env.BASE_URL}api`.replace(/\/{2,}/g, '/').replace(/\/$/, '') || '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error((data as { error?: string }).error ?? `Request failed: ${res.status}`);
  }
  return data as T;
}

function enc(path: string): string {
  return encodeURIComponent(path);
}

export const api = {
  listNotes: () => request<NoteMeta[]>('/notes'),
  getNote: (path: string) => request<NoteDetail>(`/notes/${enc(path)}`),
  createNote: (path: string, content?: string) =>
    request<NoteDetail>('/notes', {
      method: 'POST',
      body: JSON.stringify({ path, content }),
    }),
  saveNote: (path: string, content: string, title?: string) =>
    request<NoteDetail>(`/notes/${enc(path)}`, {
      method: 'PUT',
      body: JSON.stringify({ content, title }),
    }),
  deleteNote: (path: string) =>
    request<{ ok: boolean }>(`/notes/${enc(path)}`, { method: 'DELETE' }),
  search: (q: string) => request<NoteMeta[]>(`/search?q=${encodeURIComponent(q)}`),
  getGraph: () => request<GraphData>('/graph'),

  listWorkflows: () => request<Workflow[]>('/workflows'),
  getWorkflow: (id: string) => request<Workflow>(`/workflows/${enc(id)}`),
  saveWorkflow: (workflow: {
    id: string;
    name: string;
    description?: string;
    icon?: string;
    definition: WorkflowDefinition;
  }) =>
    request<Workflow>('/workflows', {
      method: 'POST',
      body: JSON.stringify(workflow),
    }),
  deleteWorkflow: (id: string) =>
    request<{ ok: boolean }>(`/workflows/${enc(id)}`, { method: 'DELETE' }),
  triggerWorkflow: (id: string, notePath?: string) =>
    request<{ executionId: string; status: string; response: unknown }>(
      `/workflows/${enc(id)}/trigger`,
      {
        method: 'POST',
        body: JSON.stringify({ notePath }),
      }
    ),
  listExecutions: () => request<Execution[]>('/executions'),

  personaStatus: () =>
    request<{ ok: boolean; url: string; detail?: unknown }>('/persona/status'),
  listPersonas: () => request<{ personas: PersonaInfo[] }>('/persona/personas'),

  capturePersonaChat: (payload: {
    personaId: string;
    personaName?: string;
    userMessage: string;
    assistantMessage: string;
    workspaceId?: string;
    mode?: string;
    sessionId?: string;
  }) =>
    request<{ ok: boolean; dailyNotePath: string; personaNotePath: string }>(
      '/persona/capture',
      { method: 'POST', body: JSON.stringify(payload) }
    ),

  listPersonaChats: () =>
    request<{ chats: NoteMeta[] }>('/persona/chats'),

  listPersonaSessions: () =>
    request<{ sessions: NoteMeta[] }>('/persona/sessions'),

  deletePersonaChat: (date: string) =>
    request<{ ok: boolean }>(`/persona/chats/${encodeURIComponent(date)}`, { method: 'DELETE' }),

  getBrainConfig: () => request<BrainConfig>('/brain/config'),
  saveBrainConfig: (config: Partial<BrainConfig>) =>
    request<BrainConfig>('/brain/config', { method: 'POST', body: JSON.stringify(config) }),

  getToday: () => request<TodayData>('/brain/today'),
  ragSearch: (q: string, limit?: number) =>
    request<RagResult>(`/brain/rag?q=${encodeURIComponent(q)}${limit ? `&limit=${limit}` : ''}`),
  ragInject: (message: string) =>
    request<{ enabled: boolean; context: string; injectedMessage: string }>('/brain/rag/inject', {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
};

export const WORKFLOW_BLOCK_REGEX = /^:::workflow\s+(\S+)/gm;

export function parseWorkflowBlocks(content: string): string[] {
  const ids: string[] = [];
  let match: RegExpExecArray | null;
  const re = new RegExp(WORKFLOW_BLOCK_REGEX.source, 'gm');
  while ((match = re.exec(content)) !== null) {
    ids.push(match[1]);
  }
  return ids;
}

export const NODE_TYPES = [
  { type: 'noteTrigger', label: 'Note Trigger', icon: '▶' },
  { type: 'captureTrigger', label: 'On Capture', icon: '💬' },
  { type: 'llm', label: 'Persona LLM', icon: '🤖' },
  { type: 'personaRag', label: 'Vault RAG', icon: '🔍' },
  { type: 'transform', label: 'Transform', icon: '⚙' },
  { type: 'branch', label: 'Branch', icon: '⑂' },
  { type: 'vaultWrite', label: 'Vault Write', icon: '📝' },
  { type: 'output', label: 'Output', icon: '📤' },
] as const;

export function defaultNodeData(type: string): Record<string, unknown> {
  switch (type) {
    case 'noteTrigger':
    case 'captureTrigger':
      return {};
    case 'personaRag':
      return { queryTemplate: '{{note.content}}', maxChunks: 5 };
    case 'branch':
      return { condition: 'return (note?.content || "").length > 0;' };
    case 'llm':
      return {
        personaId: 'byte',
        workspaceId: 'default',
        messageTemplate: '{{note.content}}',
        useRag: false,
      };
    case 'transform':
      return { code: 'return note?.content || "";' };
    case 'vaultWrite':
      return {
        action: 'append',
        notePathTemplate: '{{note.path}}',
        contentTemplate: '\n\n{{llm.output}}',
      };
    case 'output':
      return { valueTemplate: '{{llm.output}}' };
    default:
      return {};
  }
}
