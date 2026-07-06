import { useEffect, useState } from 'react';
import { api, type PersonaInfo } from '../../lib/api';

interface NodeInspectorProps {
  nodeType: string | null;
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

export default function NodeInspector({ nodeType, config, onChange }: NodeInspectorProps) {
  const [personas, setPersonas] = useState<PersonaInfo[]>([]);

  useEffect(() => {
    api.listPersonas().then((r) => setPersonas(r.personas)).catch(() => setPersonas([]));
  }, []);

  if (!nodeType) {
    return <p className="empty-state">Select a node to edit</p>;
  }

  const set = (key: string, value: unknown) => onChange({ ...config, [key]: value });

  return (
    <div>
      <h3 style={{ marginBottom: 12, fontSize: 14 }}>{nodeType}</h3>

      {nodeType === 'llm' && (
        <>
          <div className="form-group">
            <label>Persona</label>
            <select
              value={String(config.personaId ?? 'byte')}
              onChange={(e) => set('personaId', e.target.value)}
            >
              {personas.length === 0 ? (
                <option value="byte">byte (default)</option>
              ) : (
                personas.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))
              )}
            </select>
          </div>
          <div className="form-group">
            <label>Message template</label>
            <textarea
              rows={6}
              value={String(config.messageTemplate ?? '')}
              onChange={(e) => set('messageTemplate', e.target.value)}
            />
          </div>
        </>
      )}

      {nodeType === 'transform' && (
        <div className="form-group">
          <label>JavaScript code</label>
          <textarea
            rows={10}
            value={String(config.code ?? '')}
            onChange={(e) => set('code', e.target.value)}
            style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}
          />
        </div>
      )}

      {nodeType === 'vaultWrite' && (
        <>
          <div className="form-group">
            <label>Action</label>
            <select
              value={String(config.action ?? 'append')}
              onChange={(e) => set('action', e.target.value)}
            >
              <option value="append">append</option>
              <option value="create">create</option>
            </select>
          </div>
          <div className="form-group">
            <label>Note path template</label>
            <input
              value={String(config.notePathTemplate ?? '{{note.path}}')}
              onChange={(e) => set('notePathTemplate', e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Content template</label>
            <textarea
              rows={5}
              value={String(config.contentTemplate ?? '')}
              onChange={(e) => set('contentTemplate', e.target.value)}
            />
          </div>
        </>
      )}

      {nodeType === 'output' && (
        <div className="form-group">
          <label>Value template</label>
          <input
            value={String(config.valueTemplate ?? '{{llm.output}}')}
            onChange={(e) => set('valueTemplate', e.target.value)}
          />
        </div>
      )}

      {nodeType === 'noteTrigger' && (
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          Entry point when a workflow is triggered from a note.
        </p>
      )}
    </div>
  );
}
