import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const personaApp = path.join(__dirname, '..', 'persona-app');
const src = path.join(personaApp, 'src');

function pythonCommand() {
  if (process.env.PYTHON) return [process.env.PYTHON];
  if (process.platform === 'win32') {
    return ['py', '-3'];
  }
  return ['python3'];
}

const [py, ...pyArgs] = pythonCommand();
const args = [
  ...pyArgs,
  '-m',
  'uvicorn',
  'persona.web.server:app',
  '--host',
  '127.0.0.1',
  '--port',
  '8765',
  '--reload',
];

const child = spawn(py, args, {
  cwd: personaApp,
  env: {
    ...process.env,
    PYTHONPATH: src,
    PERSONA_API_URL: 'http://127.0.0.1:8765',
    BIG_BRAIN_URL: process.env.BIG_BRAIN_URL ?? 'http://127.0.0.1:3002',
  },
  stdio: 'inherit',
  shell: false,
});

child.on('exit', (code) => process.exit(code ?? 0));
