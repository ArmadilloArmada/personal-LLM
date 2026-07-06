import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type Workflow } from '../lib/api';

export default function WorkflowListPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);

  const load = async () => {
    setWorkflows(await api.listWorkflows());
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async () => {
    const id = prompt('Workflow ID (e.g. my-workflow):');
    if (!id?.trim()) return;
    const name = prompt('Display name:', id) ?? id;
    await api.saveWorkflow({
      id: id.trim(),
      name,
      description: '',
      icon: '⚡',
      definition: {
        nodes: [
          {
            id: 'trigger',
            type: 'noteTrigger',
            position: { x: 80, y: 120 },
            data: {},
          },
        ],
        edges: [],
      },
    });
    load();
  };

  const handleDelete = async (id: string) => {
    if (!confirm(`Delete workflow "${id}"?`)) return;
    await api.deleteWorkflow(id);
    load();
  };

  return (
    <div className="settings-page" style={{ maxWidth: 800 }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0, marginRight: 'auto' }}>Workflows</h2>
        <button type="button" className="primary" onClick={handleCreate}>
          New workflow
        </button>
      </div>

      {workflows.length === 0 ? (
        <p className="empty-state">No workflows yet</p>
      ) : (
        workflows.map((wf) => (
          <div key={wf.id} className="workflow-card">
            <span>{wf.icon}</span>
            <div className="info">
              <div className="name">
                <Link to={`/workflows/${wf.id}`}>{wf.name}</Link>
              </div>
              <div className="desc">
                {wf.description || wf.id} · {wf.definition.nodes.length} nodes
              </div>
            </div>
            <Link to={`/workflows/${wf.id}`}>
              <button type="button">Edit</button>
            </Link>
            <button type="button" className="danger" onClick={() => handleDelete(wf.id)}>
              Delete
            </button>
          </div>
        ))
      )}
    </div>
  );
}
