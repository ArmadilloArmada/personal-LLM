import type { NoteMeta } from '../../lib/api';

interface VaultSidebarProps {
  notes: NoteMeta[];
  activePath: string | null;
  onSelect: (path: string) => void;
  onCreate: (path: string) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  searchResults: NoteMeta[];
  onSearchSelect: (path: string) => void;
}

export default function VaultSidebar({
  notes,
  activePath,
  onSelect,
  onCreate,
  searchQuery,
  onSearchChange,
  searchResults,
  onSearchSelect,
}: VaultSidebarProps) {
  const handleNewNote = () => {
    const name = prompt('Note name (e.g. my-note.md):');
    if (name?.trim()) onCreate(name.trim());
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header" style={{ position: 'relative' }}>
        <input
          type="search"
          placeholder="Search notes..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
        />
        <button type="button" onClick={handleNewNote} title="New note">
          +
        </button>
        {searchQuery && searchResults.length > 0 && (
          <div className="search-results">
            {searchResults.map((n) => (
              <div
                key={n.path}
                className="search-result-item"
                onClick={() => onSearchSelect(n.path)}
              >
                {n.title}
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="note-tree">
        {notes.length === 0 ? (
          <p className="empty-state">No notes yet</p>
        ) : (
          notes.map((note) => (
            <div
              key={note.path}
              className={`note-item ${activePath === note.path ? 'active' : ''}`}
              onClick={() => onSelect(note.path)}
              title={note.path}
            >
              {note.title}
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
