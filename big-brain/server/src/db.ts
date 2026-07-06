import Database from 'better-sqlite3';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

function personaDataDir(): string {
  const home = process.env.USERPROFILE || process.env.HOME || os.homedir();
  const dir = path.join(home, '.persona');
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

const DB_PATH = process.env.DB_PATH ?? path.join(personaDataDir(), 'big-brain.db');
const VAULT_PATH = process.env.VAULT_PATH ?? path.join(personaDataDir(), 'vault');

export function getVaultPath(): string {
  return path.resolve(VAULT_PATH);
}

function migrateSchema(db: Database.Database): void {
  const workflowCols = db.prepare('PRAGMA table_info(workflows)').all() as Array<{ name: string }>;
  const hasDefinition = workflowCols.some((c) => c.name === 'definition');
  const hasWebhook = workflowCols.some((c) => c.name === 'webhook_url');

  if (workflowCols.length > 0 && hasWebhook && !hasDefinition) {
    db.exec(`
      CREATE TABLE workflows_new (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        icon TEXT DEFAULT '⚡',
        definition TEXT NOT NULL DEFAULT '{"nodes":[],"edges":[]}'
      );
      INSERT INTO workflows_new (id, name, description, icon, definition)
        SELECT id, name, description, icon, '{"nodes":[],"edges":[]}' FROM workflows;
      DROP TABLE workflows;
      ALTER TABLE workflows_new RENAME TO workflows;
    `);
  }

  if (workflowCols.length === 0 || !hasDefinition) {
    db.exec(`
      CREATE TABLE IF NOT EXISTS workflows (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        icon TEXT DEFAULT '⚡',
        definition TEXT NOT NULL DEFAULT '{"nodes":[],"edges":[]}'
      );
    `);
  }

  const execCols = db.prepare('PRAGMA table_info(executions)').all() as Array<{ name: string }>;
  const hasN8nResponse = execCols.some((c) => c.name === 'n8n_response');
  const hasResponse = execCols.some((c) => c.name === 'response');

  if (execCols.length > 0 && hasN8nResponse && !hasResponse) {
    db.exec(`ALTER TABLE executions RENAME COLUMN n8n_response TO response`);
  }

  if (execCols.length === 0) {
    db.exec(`
      CREATE TABLE IF NOT EXISTS executions (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        note_path TEXT,
        status TEXT NOT NULL,
        response TEXT,
        created_at TEXT NOT NULL,
        duration_ms INTEGER
      );
    `);
  }
}

export function getDb(): Database.Database {
  const dbDir = path.dirname(path.resolve(DB_PATH));
  fs.mkdirSync(dbDir, { recursive: true });
  const db = new Database(path.resolve(DB_PATH));
  db.pragma('journal_mode = WAL');
  db.exec(`
    CREATE TABLE IF NOT EXISTS notes (
      path TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      content_hash TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS links (
      source_path TEXT NOT NULL,
      target_path TEXT NOT NULL,
      PRIMARY KEY (source_path, target_path)
    );

    CREATE TABLE IF NOT EXISTS workflows (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      description TEXT DEFAULT '',
      icon TEXT DEFAULT '⚡',
      definition TEXT NOT NULL DEFAULT '{"nodes":[],"edges":[]}'
    );

    CREATE TABLE IF NOT EXISTS executions (
      id TEXT PRIMARY KEY,
      workflow_id TEXT NOT NULL,
      note_path TEXT,
      status TEXT NOT NULL,
      response TEXT,
      created_at TEXT NOT NULL,
      duration_ms INTEGER
    );

    CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS capture_dedupe (
      hash TEXT PRIMARY KEY,
      created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_path);
    CREATE INDEX IF NOT EXISTS idx_executions_created ON executions(created_at DESC);
  `);
  migrateSchema(db);
  return db;
}

export function ensureVault(): void {
  fs.mkdirSync(getVaultPath(), { recursive: true });
}
