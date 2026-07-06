import { useState } from 'react';
import type { Workflow, Execution } from '../../lib/api';

type RunStatus = 'idle' | 'running' | 'success' | 'error';

interface WorkflowPanelProps {
  workflows: Workflow[];
  executions: Execution[];
  notePath: string | null;
  onTrigger: (workflowId: string) => Promise<void>;
}

export default function WorkflowPanel({
  workflows,
  executions,
  notePath,
  onTrigger,
}: WorkflowPanelProps) {
  const [runStates, setRunStates] = useState<Record<string, RunStatus>>({});

  const handleRun = async (id: string) => {
    setRunStates((s) => ({ ...s, [id]: 'running' }));
    try {
      await onTrigger(id);
      setRunStates((s) => ({ ...s, [id]: 'success' }));
      setTimeout(() => setRunStates((s) => ({ ...s, [id]: 'idle' })), 3000);
    } catch {
      setRunStates((s) => ({ ...s, [id]: 'error' }));
      setTimeout(() => setRunStates((s) => ({ ...s, [id]: 'idle' })), 5000);
    }
  };

  return (
    <div>
      <div className="panel-section">
        <h3>Workflows</h3>
        {workflows.length === 0 ? (
          <p className="empty-state" style={{ padding: '8px 0' }}>
            No workflows yet. Create one on the Workflows page.
          </p>
        ) : (
          workflows.map((wf) => {
            const status = runStates[wf.id] ?? 'idle';
            return (
              <div key={wf.id} className="workflow-card">
                <span>{wf.icon}</span>
                <div className="info">
                  <div className="name">{wf.name}</div>
                  {wf.description && <div className="desc">{wf.description}</div>}
                </div>
                {status !== 'idle' && (
                  <span className={`status-badge ${status}`}>{status}</span>
                )}
                <button
                  type="button"
                  className="primary"
                  onClick={() => handleRun(wf.id)}
                  disabled={status === 'running' || !notePath}
                  title={notePath ? `Run on ${notePath}` : 'Open a note first'}
                >
                  Run
                </button>
              </div>
            );
          })
        )}
      </div>

      <div className="panel-section">
        <h3>Recent executions</h3>
        {executions.length === 0 ? (
          <p className="empty-state" style={{ padding: '8px 0' }}>
            No executions yet
          </p>
        ) : (
          executions.slice(0, 10).map((ex) => (
            <div key={ex.id} className="execution-row">
              <div>
                <strong>{ex.workflowName ?? ex.workflowId}</strong>
                <span className={`status-badge ${ex.status}`} style={{ marginLeft: 8 }}>
                  {ex.status}
                </span>
              </div>
              <div className="meta">
                {ex.notePath && <span>{ex.notePath} · </span>}
                {ex.durationMs}ms · {new Date(ex.createdAt).toLocaleString()}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
