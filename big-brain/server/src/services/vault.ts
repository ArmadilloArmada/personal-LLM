import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import matter from 'gray-matter';
import type Database from 'better-sqlite3';
import { ensureVault, getVaultPath } from '../db.js';
import {
  extractTags,
  extractWikilinks,
  resolveLinkTarget,
  titleFromPath,
} from '../lib/wikilinks.js';
import { classifyNote, autoTitleFromMessage, slugify } from '../lib/note-kind.js';
import type { CaptureMode } from '../shared/types.js';

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

function hashContent(content: string): string {
  return crypto.createHash('sha256').update(content).digest('hex').slice(0, 16);
}

function fullPath(notePath: string): string {
  const vault = getVaultPath();
  const resolved = path.resolve(vault, notePath);
  if (!resolved.startsWith(vault)) {
    throw new Error('Invalid note path');
  }
  return resolved;
}

function listMdFiles(dir: string, base = ''): string[] {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    if (entry.name.startsWith('.') || entry.name === '.obsidian') continue;
    const rel = base ? `${base}/${entry.name}` : entry.name;
    const abs = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...listMdFiles(abs, rel));
    } else if (entry.name.endsWith('.md')) {
      files.push(rel.replace(/\\/g, '/'));
    }
  }
  return files;
}

function parseNote(notePath: string, raw: string) {
  const { content, data } = matter(raw);
  const title =
    typeof data.title === 'string' ? data.title : titleFromPath(notePath);
  const tags = [
    ...new Set([
      ...extractTags(content),
      ...(Array.isArray(data.tags)
        ? data.tags.map((t) => String(t).toLowerCase())
        : []),
    ]),
  ];
  const wikilinks = extractWikilinks(content);
  return { content, frontmatter: data as Record<string, unknown>, title, tags, wikilinks };
}

function rebuildLinks(db: Database.Database, notePath: string, wikilinks: string[]): void {
  const allPaths = listMdFiles(getVaultPath());
  db.prepare('DELETE FROM links WHERE source_path = ?').run(notePath);
  const insert = db.prepare(
    'INSERT OR IGNORE INTO links (source_path, target_path) VALUES (?, ?)'
  );
  for (const link of wikilinks) {
    const target = resolveLinkTarget(link, allPaths);
    if (target) insert.run(notePath, target);
  }
}

export class VaultService {
  constructor(private db: Database.Database) {
    ensureVault();
    this.syncFromDisk();
  }

  syncFromDisk(): void {
    const files = listMdFiles(getVaultPath());
    const upsert = this.db.prepare(`
      INSERT INTO notes (path, title, content_hash, updated_at)
      VALUES (?, ?, ?, ?)
      ON CONFLICT(path) DO UPDATE SET
        title = excluded.title,
        content_hash = excluded.content_hash,
        updated_at = excluded.updated_at
    `);
    for (const filePath of files) {
      const raw = fs.readFileSync(fullPath(filePath), 'utf-8');
      const parsed = parseNote(filePath, raw);
      const stat = fs.statSync(fullPath(filePath));
      upsert.run(
        filePath,
        parsed.title,
        hashContent(raw),
        stat.mtime.toISOString()
      );
      rebuildLinks(this.db, filePath, parsed.wikilinks);
    }
  }

  listNotes(): NoteMeta[] {
    this.syncFromDisk();
    return this.db
      .prepare('SELECT path, title, updated_at as updatedAt FROM notes ORDER BY path')
      .all() as NoteMeta[];
  }

  getNote(notePath: string): NoteDetail | null {
    const fp = fullPath(notePath);
    if (!fs.existsSync(fp)) return null;
    const raw = fs.readFileSync(fp, 'utf-8');
    const parsed = parseNote(notePath, raw);
    const stat = fs.statSync(fp);
    const backlinks = this.db
      .prepare('SELECT source_path FROM links WHERE target_path = ?')
      .all(notePath) as { source_path: string }[];

    this.db
      .prepare(
        `INSERT INTO notes (path, title, content_hash, updated_at)
         VALUES (?, ?, ?, ?)
         ON CONFLICT(path) DO UPDATE SET title=excluded.title, content_hash=excluded.content_hash, updated_at=excluded.updated_at`
      )
      .run(notePath, parsed.title, hashContent(raw), stat.mtime.toISOString());
    rebuildLinks(this.db, notePath, parsed.wikilinks);

    return {
      path: notePath,
      title: parsed.title,
      content: parsed.content,
      frontmatter: parsed.frontmatter,
      tags: parsed.tags,
      wikilinks: parsed.wikilinks,
      backlinks: backlinks.map((b) => b.source_path),
      updatedAt: stat.mtime.toISOString(),
    };
  }

  saveNote(notePath: string, content: string, title?: string): NoteDetail {
    ensureVault();
    const fp = fullPath(notePath);
    fs.mkdirSync(path.dirname(fp), { recursive: true });

    let frontmatter: Record<string, unknown> = {};
    const existing = fs.existsSync(fp) ? fs.readFileSync(fp, 'utf-8') : '';
    if (existing) {
      frontmatter = matter(existing).data as Record<string, unknown>;
    }
    if (title) frontmatter.title = title;

    const fileContent = matter.stringify(content, frontmatter);
    fs.writeFileSync(fp, fileContent, 'utf-8');

    const parsed = parseNote(notePath, fileContent);
    const now = new Date().toISOString();
    this.db
      .prepare(
        `INSERT INTO notes (path, title, content_hash, updated_at)
         VALUES (?, ?, ?, ?)
         ON CONFLICT(path) DO UPDATE SET title=excluded.title, content_hash=excluded.content_hash, updated_at=excluded.updated_at`
      )
      .run(notePath, parsed.title, hashContent(fileContent), now);
    rebuildLinks(this.db, notePath, parsed.wikilinks);

    return this.getNote(notePath)!;
  }

  createNote(notePath: string, content = ''): NoteDetail {
    const normalized = notePath.endsWith('.md') ? notePath : `${notePath}.md`;
    if (fs.existsSync(fullPath(normalized))) {
      throw new Error('Note already exists');
    }
    return this.saveNote(normalized, content || `# ${titleFromPath(normalized)}\n\n`);
  }

  deleteNote(notePath: string): void {
    const fp = fullPath(notePath);
    if (fs.existsSync(fp)) fs.unlinkSync(fp);
    this.db.prepare('DELETE FROM notes WHERE path = ?').run(notePath);
    this.db.prepare('DELETE FROM links WHERE source_path = ? OR target_path = ?').run(
      notePath,
      notePath
    );
  }

  search(query: string): NoteMeta[] {
    this.syncFromDisk();
    const q = query.toLowerCase();
    const results: NoteMeta[] = [];
    const notes = this.listNotes();
    for (const note of notes) {
      const detail = this.getNote(note.path);
      if (!detail) continue;
      const haystack = `${detail.title} ${detail.content} ${detail.tags.join(' ')}`.toLowerCase();
      if (haystack.includes(q)) results.push(note);
    }
    return results;
  }

  getGraph(): {
    nodes: { id: string; title: string; kind: string }[];
    links: { source: string; target: string }[];
  } {
    this.syncFromDisk();
    const notes = this.listNotes();
    const linkRows = this.db.prepare('SELECT source_path, target_path FROM links').all() as {
      source_path: string;
      target_path: string;
    }[];
    return {
      nodes: notes.map((n) => ({
        id: n.path,
        title: n.title,
        kind: classifyNote(n.path),
      })),
      links: linkRows.map((l) => ({ source: l.source_path, target: l.target_path })),
    };
  }

  isDuplicateCapture(hash: string): boolean {
    const row = this.db.prepare('SELECT hash FROM capture_dedupe WHERE hash = ?').get(hash);
    return !!row;
  }

  recordCaptureHash(hash: string): void {
    this.db
      .prepare('INSERT OR IGNORE INTO capture_dedupe (hash, created_at) VALUES (?, ?)')
      .run(hash, new Date().toISOString());
  }

  private redactText(text: string): string {
    return text
      .replace(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, '[email]')
      .replace(/\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/g, '[phone]');
  }

  appendToNote(notePath: string, text: string): NoteDetail {
    const note = this.getNote(notePath);
    if (!note) throw new Error('Note not found');
    return this.saveNote(notePath, `${note.content}\n\n${text}`);
  }

  updateFrontmatter(notePath: string, updates: Record<string, unknown>): NoteDetail {
    const note = this.getNote(notePath);
    if (!note) throw new Error('Note not found');
    const merged = { ...note.frontmatter, ...updates };
    const fileContent = matter.stringify(note.content, merged);
    fs.writeFileSync(fullPath(notePath), fileContent, 'utf-8');
    return this.getNote(notePath)!;
  }

  capturePersonaChat(data: {
    personaId: string;
    personaName?: string;
    workspaceId?: string;
    userMessage: string;
    assistantMessage: string;
    mode?: string;
    sessionId?: string;
    captureMode?: CaptureMode;
    starred?: boolean;
    autoTitle?: string;
    redact?: boolean;
    skipDedupe?: boolean;
  }): {
    dailyNotePath: string;
    personaNotePath: string;
    sessionNotePath?: string;
    topicNotePath?: string;
    skipped?: boolean;
    reason?: string;
  } {
    const userMsg = data.redact ? this.redactText(data.userMessage) : data.userMessage;
    const assistantMsg = data.redact ? this.redactText(data.assistantMessage) : data.assistantMessage;

    const dedupeKey = hashContent(`${data.personaId}|${userMsg}|${assistantMsg}`);
    if (!data.skipDedupe && this.isDuplicateCapture(dedupeKey)) {
      return {
        dailyNotePath: '',
        personaNotePath: '',
        skipped: true,
        reason: 'duplicate',
      };
    }

    const personaLabel = data.personaName?.trim() || data.personaId;
    const personaSlug = personaLabel.replace(/[^\w\s-]/g, '').trim() || data.personaId;
    const personaNotePath = `Personas/${personaSlug}.md`;
    const date = new Date().toISOString().slice(0, 10);
    const dailyNotePath = `Persona/Chats/${date}.md`;
    const time = new Date().toLocaleTimeString();
    const titleHint = data.autoTitle?.trim() || autoTitleFromMessage(userMsg);

    if (!fs.existsSync(fullPath(personaNotePath))) {
      this.createNote(
        personaNotePath,
        `# ${personaLabel}

Persona agent — conversations link here from the knowledge graph.

#persona #agent
`
      );
    }

    const chatBlock = `## ${time} · [[${personaSlug}]]${data.starred ? ' ⭐' : ''}

**You:** ${userMsg.trim()}

**${personaLabel}:** ${assistantMsg.trim()}

#chat #persona${data.starred ? ' #starred' : ''}
`;

    if (!fs.existsSync(fullPath(dailyNotePath))) {
      this.createNote(
        dailyNotePath,
        `# Persona chats · ${date}

Daily log of Persona conversations. Linked agents: [[${personaSlug}]]

#persona #chat #daily
`
      );
    }
    this.appendToNote(dailyNotePath, chatBlock);

    const sessionLine = `- ${time}: [[Persona/Chats/${date}|${date} chat]]`;
    const personaNote = this.getNote(personaNotePath)!;
    if (!personaNote.content.includes(sessionLine)) {
      this.appendToNote(personaNotePath, `\n${sessionLine}`);
    }

    let sessionNotePath: string | undefined;
    if (data.sessionId) {
      sessionNotePath = `Persona/Sessions/${data.sessionId}.md`;
      if (!fs.existsSync(fullPath(sessionNotePath))) {
        this.createNote(
          sessionNotePath,
          `# Session · ${personaLabel}

Persona: [[${personaSlug}]]
Workspace: ${data.workspaceId ?? 'default'}

#persona #session
`
        );
      }
      this.appendToNote(sessionNotePath, chatBlock);
    }

    let topicNotePath: string | undefined;
    if (data.starred || data.captureMode === 'manual') {
      const topicSlug = slugify(titleHint);
      topicNotePath = `Persona/Topics/${topicSlug}.md`;
      if (!fs.existsSync(fullPath(topicNotePath))) {
        this.createNote(
          topicNotePath,
          `# ${titleHint}

Persona: [[${personaSlug}]]
Source: [[Persona/Chats/${date}]]

#persona #topic
`
        );
      }
      this.appendToNote(
        topicNotePath,
        `\n${chatBlock}\nLinked: [[${personaSlug}]] · [[Persona/Chats/${date}]]`
      );
    }

    this.recordCaptureHash(dedupeKey);
    return { dailyNotePath, personaNotePath, sessionNotePath, topicNotePath };
  }

  captureSessionSummary(data: {
    personaId: string;
    personaName?: string;
    sessionId: string;
  }): { sessionNotePath: string } {
    const sessionNotePath = `Persona/Sessions/${data.sessionId}.md`;
    const note = this.getNote(sessionNotePath);
    if (!note) {
      throw new Error('Session note not found');
    }
    const summaryBlock = `\n## Session summary · ${new Date().toLocaleTimeString()}\n\nCaptured ${note.content.split('##').length - 1} exchanges in this session.\n\n#session-summary\n`;
    this.appendToNote(sessionNotePath, summaryBlock);
    return { sessionNotePath };
  }
}
