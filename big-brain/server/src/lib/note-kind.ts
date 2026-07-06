import type { GraphNodeKind } from '../shared/types.js';

export function classifyNote(path: string): GraphNodeKind {
  if (path.startsWith('Personas/') || path === 'Personas.md') return 'persona';
  if (path.startsWith('Persona/Chats/')) return 'chat';
  if (path.startsWith('Persona/Sessions/')) return 'session';
  if (path.startsWith('Projects/')) return 'project';
  return 'note';
}

export const GRAPH_NODE_COLORS: Record<GraphNodeKind, string> = {
  persona: '#c084fc',
  chat: '#89b4fa',
  session: '#67e8f9',
  project: '#a6e3a1',
  note: '#6c7086',
};

export function slugify(text: string): string {
  return text.replace(/[^\w\s-]/g, '').trim().replace(/\s+/g, '-') || 'untitled';
}

export function autoTitleFromMessage(message: string): string {
  const line = message.split('\n')[0].trim().slice(0, 60);
  return line || 'Untitled chat';
}
