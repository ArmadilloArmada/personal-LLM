import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const personaDir = path.join(os.homedir(), '.persona');
fs.mkdirSync(path.join(personaDir, 'vault'), { recursive: true });

const serverEntry = path.join(__dirname, '..', 'big-brain', 'server', 'dist', 'index.js');
const devEntry = path.join(__dirname, '..', 'big-brain', 'server', 'src', 'index.ts');

const useDist = fs.existsSync(serverEntry);
const node = process.execPath;

const env = {
  ...process.env,
  PORT: process.env.PORT ?? '3002',
  VAULT_PATH: process.env.VAULT_PATH ?? path.join(personaDir, 'vault'),
  DB_PATH: process.env.DB_PATH ?? path.join(personaDir, 'big-brain.db'),
  PERSONA_API_URL: process.env.PERSONA_API_URL ?? 'http://127.0.0.1:8765',
};

if (useDist) {
  const child = spawn(process.platform === 'win32' ? 'node' : 'node', [serverEntry], {
    env,
    stdio: 'inherit',
    cwd: path.dirname(serverEntry),
    shell: process.platform === 'win32',
  });
  child.on('exit', (code) => process.exit(code ?? 0));
} else {
  const tsx = path.join(__dirname, '..', 'big-brain', 'node_modules', '.bin', 'tsx');
  const runner = fs.existsSync(tsx) ? tsx : 'npx';
  const args = fs.existsSync(tsx) ? ['watch', devEntry] : ['tsx', 'watch', devEntry];
  const child = spawn(runner, args, {
    env,
    stdio: 'inherit',
    cwd: path.join(__dirname, '..', 'big-brain', 'server'),
    shell: true,
  });
  child.on('exit', (code) => process.exit(code ?? 0));
}
