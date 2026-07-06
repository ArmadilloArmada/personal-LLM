const PERSONA_API_URL = process.env.PERSONA_API_URL ?? 'http://127.0.0.1:8765';
const ALLOWED_HOSTS = (process.env.PERSONA_ALLOWED_HOSTS ?? 'localhost,127.0.0.1')
  .split(',')
  .map((h) => h.trim().toLowerCase());

let configuredPersonaUrl: string | null = null;

export function setPersonaApiUrl(url: string): void {
  configuredPersonaUrl = url.replace(/\/$/, '');
}

function isAllowedUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase();
    return ALLOWED_HOSTS.some((h) => host === h || host.endsWith(`.${h}`));
  } catch {
    return false;
  }
}

export function getPersonaApiUrl(): string {
  return (configuredPersonaUrl ?? PERSONA_API_URL).replace(/\/$/, '');
}

export async function personaChat(options: {
  message: string;
  personaId: string;
  workspaceId?: string;
}): Promise<string> {
  const base = getPersonaApiUrl();
  if (!isAllowedUrl(base)) {
    throw new Error(`Persona URL host not in allowlist: ${ALLOWED_HOSTS.join(', ')}`);
  }

  const res = await fetch(`${base}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: options.message,
      persona_id: options.personaId,
      workspace_id: options.workspaceId ?? 'default',
      stream: true,
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Persona error ${res.status}: ${text}`);
  }

  if (!res.body) {
    throw new Error('Persona returned empty body');
  }

  return consumePersonaSSE(res.body);
}

async function consumePersonaSSE(body: ReadableStream<Uint8Array>): Promise<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let output = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() ?? '';

    for (const part of parts) {
      const lines = part.split('\n');
      let eventType = 'message';
      let data: Record<string, unknown> = {};
      for (const line of lines) {
        if (line.startsWith('event: ')) eventType = line.slice(7).trim();
        if (line.startsWith('data: ')) {
          try {
            data = JSON.parse(line.slice(6)) as Record<string, unknown>;
          } catch {
            data = {};
          }
        }
      }
      if (eventType === 'token') {
        output += String(data.text ?? '');
      }
      if (eventType === 'error') {
        throw new Error(String(data.message ?? 'Persona stream error'));
      }
    }
  }

  return output.trim();
}

export async function personaHealthCheck(): Promise<{ ok: boolean; detail?: unknown }> {
  try {
    const base = getPersonaApiUrl();
    const res = await fetch(`${base}/api/status`);
    if (!res.ok) return { ok: false };
    const detail = await res.json();
    return { ok: true, detail };
  } catch {
    return { ok: false };
  }
}

export async function listPersonas(): Promise<
  Array<{ id: string; name: string; role?: string }>
> {
  const base = getPersonaApiUrl();
  const res = await fetch(`${base}/api/personas`);
  if (!res.ok) return [];
  const data = (await res.json()) as { personas?: Array<{ id: string; name: string; role?: string }> };
  return data.personas ?? [];
}
