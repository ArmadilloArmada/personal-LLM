import type { WorkflowDefinition } from './types.js';

function edge(id: string, source: string, target: string) {
  return { id, source, target };
}

function pos(x: number, y: number) {
  return { x, y };
}

export const SEED_WORKFLOWS: Array<{
  id: string;
  name: string;
  description: string;
  icon: string;
  definition: WorkflowDefinition;
}> = [
  {
    id: 'summarize-note',
    name: 'Summarize Note',
    description: 'Send note to Persona and append summary',
    icon: '📝',
    definition: {
      nodes: [
        { id: 'trigger', type: 'noteTrigger', position: pos(0, 0), data: {} },
        {
          id: 'llm',
          type: 'llm',
          position: pos(220, 0),
          data: {
            personaId: 'byte',
            messageTemplate:
              'Summarize the following note titled "{{note.title}}" in 3-5 bullet points:\n\n{{note.content}}',
          },
        },
        {
          id: 'write',
          type: 'vaultWrite',
          position: pos(440, 0),
          data: {
            action: 'append',
            notePathTemplate: '{{note.path}}',
            contentTemplate: '\n\n## Summary\n{{llm.output}}',
          },
        },
      ],
      edges: [edge('e1', 'trigger', 'llm'), edge('e2', 'llm', 'write')],
    },
  },
  {
    id: 'extract-tasks',
    name: 'Extract Tasks',
    description: 'Parse checklist items and append as tasks section',
    icon: '✅',
    definition: {
      nodes: [
        { id: 'trigger', type: 'noteTrigger', position: pos(0, 0), data: {} },
        {
          id: 'transform',
          type: 'transform',
          position: pos(220, 0),
          data: {
            code: `
              const lines = (note?.content || '').split('\\n');
              const tasks = lines
                .filter(l => /^\\s*[-*]\\s+\\[[ x]\\]/i.test(l) || /^\\s*[-*]\\s+TODO/i.test(l))
                .map(l => l.replace(/^\\s*[-*]\\s+/, '').trim());
              return tasks.length ? tasks.join('\\n') : 'No tasks found.';
            `,
          },
        },
        {
          id: 'write',
          type: 'vaultWrite',
          position: pos(440, 0),
          data: {
            action: 'append',
            notePathTemplate: '{{note.path}}',
            contentTemplate: '\n\n## Extracted Tasks\n{{transform.output}}',
          },
        },
      ],
      edges: [edge('e1', 'trigger', 'transform'), edge('e2', 'transform', 'write')],
    },
  },
  {
    id: 'daily-digest',
    name: 'Daily Digest',
    description: 'Build a digest snippet from note metadata via Persona',
    icon: '📬',
    definition: {
      nodes: [
        { id: 'trigger', type: 'noteTrigger', position: pos(0, 0), data: {} },
        {
          id: 'llm',
          type: 'llm',
          position: pos(220, 0),
          data: {
            personaId: 'byte',
            messageTemplate:
              'Write a one-paragraph daily digest entry for note "{{note.title}}" (tags: {{note.tags}}):\n\n{{note.content}}',
          },
        },
        {
          id: 'out',
          type: 'output',
          position: pos(440, 0),
          data: { valueTemplate: '{{llm.output}}' },
        },
      ],
      edges: [edge('e1', 'trigger', 'llm'), edge('e2', 'llm', 'out')],
    },
  },
  {
    id: 'capture-auto-title',
    name: 'Auto-title starred chats',
    description: 'On Persona capture, create topic note title from first user line',
    icon: '⭐',
    definition: {
      nodes: [
        { id: 'trigger', type: 'captureTrigger', position: pos(0, 0), data: {} },
        {
          id: 'branch',
          type: 'branch',
          position: pos(200, 0),
          data: {
            condition: `return (capture?.userMessage || '').length > 20;`,
          },
        },
        {
          id: 'llm',
          type: 'llm',
          position: pos(420, -60),
          data: {
            personaId: 'byte',
            messageTemplate:
              'Suggest a 5-word title for this chat exchange:\nUser: {{capture.userMessage}}\nAssistant: {{capture.assistantMessage}}',
          },
        },
        {
          id: 'write',
          type: 'vaultWrite',
          position: pos(640, -60),
          data: {
            action: 'append',
            notePathTemplate: '{{capture.dailyNotePath}}',
            contentTemplate: '\n\n<!-- auto-title: {{llm.output}} -->',
          },
        },
      ],
      edges: [
        edge('e1', 'trigger', 'branch'),
        { id: 'e2', source: 'branch', target: 'llm', when: 'true' },
        edge('e3', 'llm', 'write'),
      ],
    },
  },
  {
    id: 'rag-answer',
    name: 'RAG Answer',
    description: 'Search vault for context then ask Persona',
    icon: '🔍',
    definition: {
      nodes: [
        { id: 'trigger', type: 'noteTrigger', position: pos(0, 0), data: {} },
        {
          id: 'rag',
          type: 'personaRag',
          position: pos(200, 0),
          data: { queryTemplate: '{{note.title}} {{note.content}}', maxChunks: 5 },
        },
        {
          id: 'llm',
          type: 'llm',
          position: pos(420, 0),
          data: {
            personaId: 'byte',
            useRag: true,
            messageTemplate: 'Using vault context above, answer based on note "{{note.title}}":\n{{note.content}}',
          },
        },
        {
          id: 'write',
          type: 'vaultWrite',
          position: pos(640, 0),
          data: {
            action: 'append',
            notePathTemplate: '{{note.path}}',
            contentTemplate: '\n\n## RAG Answer\n{{llm.output}}',
          },
        },
      ],
      edges: [edge('e1', 'trigger', 'rag'), edge('e2', 'rag', 'llm'), edge('e3', 'llm', 'write')],
    },
  },
  {
    id: 'notify-digest',
    name: 'Capture digest line',
    description: 'Append one-line digest on each Persona capture',
    icon: '📣',
    definition: {
      nodes: [
        { id: 'trigger', type: 'captureTrigger', position: pos(0, 0), data: {} },
        {
          id: 'transform',
          type: 'transform',
          position: pos(220, 0),
          data: {
            code: `
              const u = (capture?.userMessage || '').slice(0, 80);
              const a = (capture?.assistantMessage || '').slice(0, 120);
              return '- **' + (capture?.personaName || 'Persona') + '**: ' + u + ' → ' + a;
            `,
          },
        },
        {
          id: 'write',
          type: 'vaultWrite',
          position: pos(440, 0),
          data: {
            action: 'append',
            notePathTemplate: 'Persona/Digest.md',
            contentTemplate: '\n{{transform.output}}',
          },
        },
      ],
      edges: [edge('e1', 'trigger', 'transform'), edge('e2', 'transform', 'write')],
    },
  },
];
