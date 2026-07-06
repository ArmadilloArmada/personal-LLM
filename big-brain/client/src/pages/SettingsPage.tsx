import { useEffect, useState } from 'react';
import { api, type BrainConfig } from '../lib/api';

const PERSONA_URL = import.meta.env.VITE_PERSONA_URL ?? 'http://127.0.0.1:8765';
const BRAIN_CLIENT = import.meta.env.VITE_BRAIN_URL ?? 'http://localhost:5174';

export default function SettingsPage() {
  const [personaStatus, setPersonaStatus] = useState<{
    ok: boolean;
    url: string;
    detail?: unknown;
  } | null>(null);
  const [config, setConfig] = useState<BrainConfig | null>(null);
  const [message, setMessage] = useState('');
  const [chatNotes, setChatNotes] = useState<{ path: string; title: string }[]>([]);
  const [ragQuery, setRagQuery] = useState('');
  const [ragPreview, setRagPreview] = useState('');

  useEffect(() => {
    api.personaStatus().then(setPersonaStatus).catch(() => setPersonaStatus(null));
    api.getBrainConfig().then(setConfig).catch(() => setConfig(null));
    api.listPersonaChats().then((r) => setChatNotes(r.chats)).catch(() => setChatNotes([]));
  }, []);

  const refreshStatus = async () => {
    setMessage('Checking...');
    try {
      const [status, cfg, chats] = await Promise.all([
        api.personaStatus(),
        api.getBrainConfig(),
        api.listPersonaChats(),
      ]);
      setPersonaStatus(status);
      setConfig(cfg);
      setChatNotes(chats.chats);
      setMessage(status.ok ? 'Persona is reachable' : 'Persona is not running');
    } catch {
      setMessage('Could not reach services');
    }
  };

  const saveConfig = async (patch: Partial<BrainConfig>) => {
    const next = await api.saveBrainConfig(patch);
    setConfig(next);
    setMessage('Settings saved');
  };

  const testRag = async () => {
    if (!ragQuery.trim()) return;
    const r = await api.ragSearch(ragQuery);
    setRagPreview(r.context || 'No matches');
  };

  const deleteChat = async (path: string) => {
    const date = path.replace('Persona/Chats/', '').replace('.md', '');
    if (!confirm(`Delete chat log for ${date}?`)) return;
    await api.deletePersonaChat(date);
    setChatNotes((prev) => prev.filter((n) => n.path !== path));
  };

  return (
    <div className="settings-page">
      <h2>Persona + Big Brain</h2>
      <p style={{ color: 'var(--text-muted)', marginBottom: 24, fontSize: 14 }}>
        Configure capture, RAG context injection, and privacy. Persona embed URL:{' '}
        <code>{BRAIN_CLIENT}/embed</code>
      </p>

      <div className="form-group">
        <label>Persona app</label>
        <a href={PERSONA_URL} target="_blank" rel="noreferrer">
          Open Persona →
        </a>
      </div>

      <div className="form-group">
        <label>Connection</label>
        <p>
          {personaStatus === null ? (
            'Loading...'
          ) : personaStatus.ok ? (
            <span className="status-badge success">Connected</span>
          ) : (
            <span className="status-badge error">Not reachable — start Persona first</span>
          )}
        </p>
        <button type="button" onClick={refreshStatus} style={{ marginTop: 8 }}>
          Refresh
        </button>
        {message && (
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 8 }}>{message}</p>
        )}
      </div>

      {config && (
        <>
          <h2 style={{ marginTop: 40 }}>Capture</h2>
          <div className="settings-grid">
            <label className="settings-check">
              <input
                type="checkbox"
                checked={config.captureEnabled}
                onChange={(e) => saveConfig({ captureEnabled: e.target.checked })}
              />
              Capture enabled globally
            </label>
            <div className="form-group">
              <label>Capture mode</label>
              <select
                value={config.captureMode}
                onChange={(e) =>
                  saveConfig({
                    captureMode: e.target.value as BrainConfig['captureMode'],
                  })
                }
              >
                <option value="every_turn">Every turn</option>
                <option value="starred">Starred only</option>
                <option value="manual">Manual (/brain save)</option>
                <option value="session_end">Session end</option>
              </select>
            </div>
          </div>

          <h2 style={{ marginTop: 40 }}>RAG (vault context)</h2>
          <div className="settings-grid">
            <label className="settings-check">
              <input
                type="checkbox"
                checked={config.ragEnabled}
                onChange={(e) => saveConfig({ ragEnabled: e.target.checked })}
              />
              Inject vault context into Persona messages
            </label>
            <div className="form-group">
              <label>Max chunks</label>
              <input
                type="number"
                min={1}
                max={20}
                value={config.ragMaxChunks}
                onChange={(e) => saveConfig({ ragMaxChunks: Number(e.target.value) })}
              />
            </div>
          </div>
          <div className="form-group" style={{ marginTop: 16 }}>
            <label>Test RAG search</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                value={ragQuery}
                onChange={(e) => setRagQuery(e.target.value)}
                placeholder="Search vault..."
                style={{ flex: 1 }}
              />
              <button type="button" onClick={testRag}>
                Search
              </button>
            </div>
            {ragPreview && (
              <pre className="rag-preview">{ragPreview}</pre>
            )}
          </div>
        </>
      )}

      <h2 style={{ marginTop: 40 }}>Captured Persona chats</h2>
      {chatNotes.length === 0 ? (
        <p className="empty-state" style={{ textAlign: 'left', padding: '8px 0' }}>
          No chats captured yet. Run the install script or enable capture in Persona.
        </p>
      ) : (
        <ul className="panel-list">
          {chatNotes.map((n) => (
            <li key={n.path} className="chat-row">
              <a href={`/?note=${encodeURIComponent(n.path)}`}>{n.title || n.path}</a>
              <button type="button" className="btn-danger-sm" onClick={() => deleteChat(n.path)}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}

      <h2 style={{ marginTop: 40 }}>Persona integration</h2>
      <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
        Run <code>integrations/big-brain/install-capture.ps1</code> to copy the bridge into your
        Persona portable app. Commands in Persona chat: <code>/brain save</code>,{' '}
        <code>/brain on</code>, <code>/brain off</code>, <code>/brain graph</code>,{' '}
        <code>/brain search &lt;query&gt;</code>
      </p>

      <h2 style={{ marginTop: 40 }}>Startup</h2>
      <pre className="code-block">
        {`cd Persona
npm install
npm run dev
# Big Brain: http://localhost:5174
# Persona:   http://localhost:8765 (if portable installed)`}
      </pre>
    </div>
  );
}
