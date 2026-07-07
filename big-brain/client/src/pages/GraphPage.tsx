import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ForceGraph2D from 'react-force-graph-2d';
import { api, type GraphData, GRAPH_COLORS } from '../lib/api';

const KINDS = ['all', 'persona', 'chat', 'session', 'project', 'note'] as const;

export default function GraphPage({ embedded = false }: { embedded?: boolean }) {
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [filter, setFilter] = useState<(typeof KINDS)[number]>('all');
  const [orphansOnly, setOrphansOnly] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const navigate = useNavigate();

  const loadGraph = useCallback(async () => {
    const data = await api.getGraph();
    setGraph(data);
  }, []);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const filtered = graph
    ? (() => {
        let nodes = graph.nodes;
        if (filter !== 'all') {
          nodes = nodes.filter((n) => (n.kind ?? 'note') === filter);
        }
        const nodeIds = new Set(nodes.map((n) => n.id));
        const links = graph.links.filter((l) => nodeIds.has(l.source) && nodeIds.has(l.target));
        if (orphansOnly) {
          const linked = new Set<string>();
          for (const l of links) {
            linked.add(l.source);
            linked.add(l.target);
          }
          nodes = nodes.filter((n) => !linked.has(n.id));
        }
        return { nodes, links };
      })()
    : null;

  const handleNodeClick = (node: { id?: string }) => {
    if (node.id) {
      if (embedded) {
        sessionStorage.setItem('big-brain-open-note', node.id);
        window.parent.postMessage({ type: 'big-brain-open-note', path: node.id }, '*');
      } else {
        navigate('/');
        sessionStorage.setItem('big-brain-open-note', node.id);
      }
    }
  };

  return (
    <div className={`graph-container${embedded ? " embedded" : ""}`}>
      <div className="graph-toolbar">
        <button type="button" onClick={loadGraph}>
          Refresh
        </button>
        <select value={filter} onChange={(e) => setFilter(e.target.value as typeof filter)}>
          {KINDS.map((k) => (
            <option key={k} value={k}>
              {k === "all" ? "All types" : k}
            </option>
          ))}
        </select>
        <label className="graph-filter-check">
          <input
            type="checkbox"
            checked={orphansOnly}
            onChange={(e) => setOrphansOnly(e.target.checked)}
          />
          Orphans only
        </label>
        <span className="graph-stats">
          {filtered ? `${filtered.nodes.length} notes · ${filtered.links.length} links` : "Loading..."}
        </span>
      </div>
      <div className="graph-canvas" ref={containerRef}>
        {filtered && filtered.nodes.length > 0 ? (
          <ForceGraph2D
            width={dimensions.width}
            height={dimensions.height}
            graphData={filtered}
            nodeLabel={(n) => (n as { title?: string }).title ?? (n as { id: string }).id}
            nodeColor={(n) => GRAPH_COLORS[(n as { kind?: string }).kind ?? "note"] ?? GRAPH_COLORS.note}
            linkColor={() => "#45475a"}
            backgroundColor="#11111b"
            onNodeClick={(node) => handleNodeClick(node as { id?: string })}
          />
        ) : (
          <p className="empty-state">No notes to display in graph</p>
        )}
      </div>
    </div>
  );
}
