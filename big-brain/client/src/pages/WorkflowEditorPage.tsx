import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { api, defaultNodeData, NODE_TYPES, type Workflow } from '../lib/api';
import NodeInspector from '../components/workflow/NodeInspector';
import WorkflowNode from '../components/workflow/WorkflowNode';

const nodeTypes = { workflowNode: WorkflowNode };

export default function WorkflowEditorPage() {
  const { id } = useParams<{ id: string }>();
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const load = useCallback(async () => {
    if (!id) return;
    const wf = await api.getWorkflow(id);
    setWorkflow(wf);
    setNodes(
      wf.definition.nodes.map((n) => ({
        id: n.id,
        type: 'workflowNode',
        position: n.position,
        data: { label: n.type, nodeType: n.type, config: n.data },
      }))
    );
    setEdges(wf.definition.edges.map((e) => ({ ...e, type: 'default' })));
  }, [id, setNodes, setEdges]);

  useEffect(() => {
    load();
  }, [load]);

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge({ ...connection, id: `e-${Date.now()}` }, eds));
    },
    [setEdges]
  );

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedId) ?? null,
    [nodes, selectedId]
  );

  const addNode = (type: string) => {
    const nodeId = `${type}-${Date.now()}`;
    setNodes((nds) => [
      ...nds,
      {
        id: nodeId,
        type: 'workflowNode',
        position: { x: 120 + nds.length * 40, y: 80 + nds.length * 30 },
        data: { label: type, nodeType: type, config: defaultNodeData(type) },
      },
    ]);
  };

  const updateSelectedConfig = (config: Record<string, unknown>) => {
    if (!selectedId) return;
    setNodes((nds) =>
      nds.map((n) =>
        n.id === selectedId ? { ...n, data: { ...n.data, config } } : n
      )
    );
  };

  const handleSave = async () => {
    if (!workflow) return;
    setMessage('');
    const definition = {
      nodes: nodes.map((n) => ({
        id: n.id,
        type: String(n.data.nodeType),
        position: n.position,
        data: (n.data.config as Record<string, unknown>) ?? {},
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
      })),
    };
    await api.saveWorkflow({
      id: workflow.id,
      name: workflow.name,
      description: workflow.description,
      icon: workflow.icon,
      definition,
    });
    setMessage('Saved');
  };

  const handleTestRun = async () => {
    if (!workflow) return;
    setMessage('Running...');
    try {
      const notePath = prompt('Note path to test with (e.g. Welcome.md):', 'Welcome.md');
      const result = await api.triggerWorkflow(workflow.id, notePath || undefined);
      setMessage(`Success: ${JSON.stringify(result.response).slice(0, 120)}...`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Run failed');
    }
  };

  if (!workflow) {
    return <p className="empty-state">Loading workflow...</p>;
  }

  return (
    <div className="workflow-editor-layout">
      <aside className="workflow-palette">
        <Link to="/workflows" style={{ fontSize: 13, display: 'block', marginBottom: 12 }}>
          ← Back
        </Link>
        <h3>{workflow.icon} {workflow.name}</h3>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
          {workflow.description || workflow.id}
        </p>
        <h4 style={{ fontSize: 11, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
          Add node
        </h4>
        {NODE_TYPES.map((nt) => (
          <button
            key={nt.type}
            type="button"
            className="palette-btn"
            onClick={() => addNode(nt.type)}
          >
            {nt.icon} {nt.label}
          </button>
        ))}
        <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <button type="button" className="primary" onClick={handleSave}>
            Save
          </button>
          <button type="button" onClick={handleTestRun}>
            Test run
          </button>
        </div>
        {message && (
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 12 }}>{message}</p>
        )}
      </aside>

      <div className="workflow-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={(_, node) => setSelectedId(node.id)}
          nodeTypes={nodeTypes}
          fitView
        >
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>

      <aside className="workflow-inspector">
        <NodeInspector
          nodeType={selectedNode ? String(selectedNode.data.nodeType) : null}
          config={(selectedNode?.data.config as Record<string, unknown>) ?? {}}
          onChange={updateSelectedConfig}
        />
      </aside>
    </div>
  );
}
