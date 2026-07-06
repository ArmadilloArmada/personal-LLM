import Fastify from 'fastify';
import cors from '@fastify/cors';
import rateLimit from '@fastify/rate-limit';
import fastifyStatic from '@fastify/static';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { getDb, ensureVault, getVaultPath } from './db.js';
import { VaultService } from './services/vault.js';
import { WorkflowEngine } from './services/workflow-engine.js';
import { SettingsService } from './services/settings.js';
import { notesRoutes } from './routes/notes.js';
import { workflowRoutes } from './routes/workflows.js';
import { personaCaptureRoutes } from './routes/persona-capture.js';
import { brainRoutes } from './routes/brain.js';
import { setPersonaApiUrl } from './services/persona.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT ?? 3002);

async function seedDemoNotes(vault: VaultService) {
  const vaultPath = getVaultPath();
  const personasIndex = path.join(vaultPath, 'Personas.md');
  if (!fs.existsSync(personasIndex)) {
    vault.createNote(
      'Personas.md',
      `# Personas

Index of Persona agents linked in your knowledge graph. Chat logs live under [[Persona/Chats]].

#persona
`
    );
  }
  const welcomePath = path.join(vaultPath, 'Welcome.md');
  if (!fs.existsSync(welcomePath)) {
    vault.createNote(
      'Welcome.md',
      `# Welcome to Big Brain

Your Obsidian-like knowledge graph — powered by Persona conversations and native workflows.

## Features

- [[Getting Started]] — setup guide
- [[Personas]] — index of Persona agents in your graph
- Markdown with \`[[wiki-links]]\`
- Persona chats auto-saved to \`Persona/Chats/\`
- Workflow automations from any note

Try opening **Getting Started** from the sidebar.
`
    );
  }
  const gettingStartedPath = path.join(vaultPath, 'Getting Started.md');
  if (!fs.existsSync(gettingStartedPath)) {
    vault.createNote(
      'Getting Started.md',
      `# Getting Started

1. Start **Persona** (default http://127.0.0.1:8765) with Big Brain capture enabled
2. Chat in Persona — conversations appear in [[Persona/Chats]] notes
3. Open **Workflows** to automate on your knowledge graph
4. View **Graph** to see how personas and notes connect

Links back to [[Welcome]].

## Persona integration

Every Persona chat is captured into this vault with wiki-links to agent profiles in \`Personas/\`.

See also: [[Personas]]
`
    );
  }
  const digestPath = path.join(vaultPath, 'Persona', 'Digest.md');
  if (!fs.existsSync(digestPath)) {
    vault.createNote(
      'Persona/Digest.md',
      `# Persona capture digest

One-line summaries from capture workflows.

#persona #digest
`
    );
  }
}

async function main() {
  ensureVault();
  const db = getDb();
  const vault = new VaultService(db);
  const settings = new SettingsService(db);
  const engine = new WorkflowEngine(db, vault);

  const brainCfg = settings.getBrainConfig();
  setPersonaApiUrl(brainCfg.personaApiUrl || process.env.PERSONA_API_URL || 'http://127.0.0.1:8765');

  await seedDemoNotes(vault);
  engine.seedWorkflows();

  const app = Fastify({ logger: true });

  await app.register(cors, { origin: true });
  await app.register(rateLimit, {
    max: Number(process.env.RATE_LIMIT_MAX ?? 30),
    timeWindow: Number(process.env.RATE_LIMIT_WINDOW_MS ?? 60000),
  });

  await notesRoutes(app, vault);
  await workflowRoutes(app, engine, vault);
  await brainRoutes(app, vault, settings);
  await personaCaptureRoutes(app, vault, settings, engine);

  const clientDist = path.resolve(__dirname, '../../client/dist');
  if (fs.existsSync(clientDist)) {
    await app.register(fastifyStatic, {
      root: clientDist,
      prefix: '/',
    });
    app.setNotFoundHandler((req, reply) => {
      if (req.url.startsWith('/api')) {
        return reply.status(404).send({ error: 'Not found' });
      }
      return reply.sendFile('index.html');
    });
  }

  app.get('/api/health', async () => ({
    ok: true,
    name: 'Big Brain',
    vault: getVaultPath(),
    personaUrl: process.env.PERSONA_API_URL ?? 'http://127.0.0.1:8765',
  }));

  await app.listen({ port: PORT, host: process.env.HOST ?? '127.0.0.1' });
  console.log(`Big Brain API running on http://localhost:${PORT}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
