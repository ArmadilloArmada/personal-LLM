import type Database from 'better-sqlite3';
import type { BrainConfig, CaptureMode } from '../shared/types.js';
import { DEFAULT_BRAIN_CONFIG } from '../shared/types.js';

export class SettingsService {
  constructor(private db: Database.Database) {}

  get(key: string): string | null {
    const row = this.db.prepare('SELECT value FROM settings WHERE key = ?').get(key) as
      | { value: string }
      | undefined;
    return row?.value ?? null;
  }

  set(key: string, value: string): void {
    this.db
      .prepare(
        `INSERT INTO settings (key, value) VALUES (?, ?)
         ON CONFLICT(key) DO UPDATE SET value = excluded.value`
      )
      .run(key, value);
  }

  getBrainConfig(): BrainConfig {
    const raw = this.get('brain_config');
    if (!raw) return { ...DEFAULT_BRAIN_CONFIG };
    try {
      return { ...DEFAULT_BRAIN_CONFIG, ...JSON.parse(raw) };
    } catch {
      return { ...DEFAULT_BRAIN_CONFIG };
    }
  }

  setBrainConfig(config: Partial<BrainConfig>): BrainConfig {
    const merged = { ...this.getBrainConfig(), ...config };
    this.set('brain_config', JSON.stringify(merged));
    return merged;
  }

  getCaptureMode(): CaptureMode {
    return this.getBrainConfig().captureMode;
  }

  isCaptureEnabled(workspaceId?: string): boolean {
    const cfg = this.getBrainConfig();
    if (!cfg.captureEnabled) return false;
    if (workspaceId) {
      const off = this.get(`capture_off_${workspaceId}`);
      if (off === '1') return false;
    }
    return true;
  }
}
