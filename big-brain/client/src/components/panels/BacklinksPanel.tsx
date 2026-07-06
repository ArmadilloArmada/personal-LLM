import type { NoteDetail } from '../../lib/api';

interface BacklinksPanelProps {
  note: NoteDetail | null;
  onNavigate: (path: string) => void;
}

export default function BacklinksPanel({ note, onNavigate }: BacklinksPanelProps) {
  if (!note) {
    return <p className="empty-state">Select a note to see backlinks</p>;
  }

  return (
    <div>
      <div className="panel-section">
        <h3>Outgoing links</h3>
        {note.wikilinks.length === 0 ? (
          <p className="empty-state" style={{ padding: '8px 0' }}>
            No wiki-links
          </p>
        ) : (
          <ul className="panel-list">
            {note.wikilinks.map((link) => (
              <li key={link}>
                <button type="button" className="link" onClick={() => onNavigate(`${link}.md`)}>
                  {link}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="panel-section">
        <h3>Backlinks</h3>
        {note.backlinks.length === 0 ? (
          <p className="empty-state" style={{ padding: '8px 0' }}>
            No backlinks
          </p>
        ) : (
          <ul className="panel-list">
            {note.backlinks.map((path) => (
              <li key={path}>
                <button type="button" className="link" onClick={() => onNavigate(path)}>
                  {path.replace(/\.md$/, '')}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="panel-section">
        <h3>Tags</h3>
        {note.tags.length === 0 ? (
          <p className="empty-state" style={{ padding: '8px 0' }}>
            No tags
          </p>
        ) : (
          <div>
            {note.tags.map((tag) => (
              <span key={tag} className="tag">
                #{tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
