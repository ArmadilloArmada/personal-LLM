import { useCallback, useEffect, useRef, useState } from 'react';
import {
  api,
  parseWorkflowBlocks,
  type NoteDetail,
  type NoteMeta,
  type Workflow,
  type Execution,
} from '../lib/api';
import VaultSidebar from '../components/sidebar/VaultSidebar';
import MarkdownEditor from '../components/editor/MarkdownEditor';
import BacklinksPanel from '../components/panels/BacklinksPanel';
import WorkflowPanel from '../components/panels/WorkflowPanel';

type PanelTab = 'backlinks' | 'workflows';

export default function VaultPage({ embedded = false }: { embedded?: boolean }) {
  const [notes, setNotes] = useState<NoteMeta[]>([]);
  const [activePath, setActivePath] = useState<string | null>(null);
  const [note, setNote] = useState<NoteDetail | null>(null);
  const [content, setContent] = useState('');
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [panelTab, setPanelTab] = useState<PanelTab>('backlinks');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<NoteMeta[]>([]);
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'unsaved'>('saved');
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadNotes = useCallback(async () => {
    const list = await api.listNotes();
    setNotes(list);
    return list;
  }, []);

  const loadWorkflows = useCallback(async () => {
    const [wfs, execs] = await Promise.all([
      api.listWorkflows(),
      api.listExecutions(),
    ]);
    setWorkflows(wfs);
    setExecutions(execs);
  }, []);

  const openNote = useCallback(async (path: string) => {
    const detail = await api.getNote(path);
    setActivePath(path);
    setNote(detail);
    setContent(detail.content);
    setSaveStatus('saved');
  }, []);

  useEffect(() => {
    const pending = sessionStorage.getItem('big-brain-open-note');
    if (pending) {
      sessionStorage.removeItem('big-brain-open-note');
      setActivePath(pending);
    }
    loadNotes().then((list) => {
      if (!pending && list.length > 0) {
        setActivePath((current) => current ?? list[0].path);
      }
    });
    loadWorkflows();
  }, [loadNotes, loadWorkflows]);

  useEffect(() => {
    if (activePath) openNote(activePath);
  }, [activePath, openNote]);

  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      const results = await api.search(searchQuery);
      setSearchResults(results);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const scheduleSave = useCallback(
    (newContent: string) => {
      setContent(newContent);
      setSaveStatus('unsaved');
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(async () => {
        if (!activePath) return;
        setSaveStatus('saving');
        try {
          const updated = await api.saveNote(activePath, newContent);
          setNote(updated);
          setSaveStatus('saved');
          loadNotes();
        } catch {
          setSaveStatus('unsaved');
        }
      }, 800);
    },
    [activePath, loadNotes]
  );

  const handleCreate = async (path: string) => {
    const created = await api.createNote(path);
    await loadNotes();
    setActivePath(created.path);
  };

  const handleTrigger = async (workflowId: string) => {
    await api.triggerWorkflow(workflowId, activePath ?? undefined);
    const execs = await api.listExecutions();
    setExecutions(execs);
  };

  const workflowBlocks = note ? parseWorkflowBlocks(content) : [];

  return (
    <div className={`vault-layout${embedded ? ' embedded' : ''}`}>
      <VaultSidebar
        notes={notes}
        activePath={activePath}
        onSelect={setActivePath}
        onCreate={handleCreate}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        searchResults={searchResults}
        onSearchSelect={(path) => {
          setSearchQuery('');
          setActivePath(path);
        }}
      />

      <main className="editor-pane">
        {note ? (
          <>
            <div className="editor-toolbar">
              <span className="note-title">{note.title}</span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {saveStatus === 'saving' ? 'Saving...' : saveStatus === 'unsaved' ? 'Unsaved' : 'Saved'}
              </span>
              <select
                onChange={(e) => {
                  const id = e.target.value;
                  if (id) handleTrigger(id);
                  e.target.value = '';
                }}
                defaultValue=""
                style={{ width: 'auto' }}
              >
                <option value="" disabled>
                  Run workflow...
                </option>
                {workflows.map((wf) => (
                  <option key={wf.id} value={wf.id}>
                    {wf.icon} {wf.name}
                  </option>
                ))}
              </select>
            </div>

            {workflowBlocks.length > 0 && (
              <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border)' }}>
                {workflowBlocks.map((id) => {
                  const wf = workflows.find((w) => w.id === id);
                  if (!wf) return null;
                  return (
                    <div key={id} className="workflow-block">
                      <strong>
                        {wf.icon} {wf.name}
                      </strong>
                      <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '4px 0 8px' }}>
                        {wf.description || `Workflow: ${id}`}
                      </p>
                      <button type="button" className="primary" onClick={() => handleTrigger(id)}>
                        Run workflow
                      </button>
                    </div>
                  );
                })}
              </div>
            )}

            <div className="editor-content">
              <MarkdownEditor value={content} onChange={scheduleSave} />
            </div>
          </>
        ) : (
          <p className="empty-state">Select or create a note to begin</p>
        )}
      </main>

      <aside className="right-panel">
        <div className="panel-tabs">
          <button
            type="button"
            className={`panel-tab ${panelTab === 'backlinks' ? 'active' : ''}`}
            onClick={() => setPanelTab('backlinks')}
          >
            Links
          </button>
          <button
            type="button"
            className={`panel-tab ${panelTab === 'workflows' ? 'active' : ''}`}
            onClick={() => setPanelTab('workflows')}
          >
            Workflows
          </button>
        </div>
        <div className="panel-body">
          {panelTab === 'backlinks' ? (
            <BacklinksPanel note={note} onNavigate={setActivePath} />
          ) : (
            <WorkflowPanel
              workflows={workflows}
              executions={executions}
              notePath={activePath}
              onTrigger={handleTrigger}
            />
          )}
        </div>
      </aside>
    </div>
  );
}
