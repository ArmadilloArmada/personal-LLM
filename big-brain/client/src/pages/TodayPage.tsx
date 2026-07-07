import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { api, type TodayData } from '../lib/api';

export default function TodayPage({
  embedded = false,
  onOpenNote,
}: {
  embedded?: boolean;
  onOpenNote?: (path: string) => void;
}) {
  const [data, setData] = useState<TodayData | null>(null);

  useEffect(() => {
    api.getToday().then(setData).catch(() => setData(null));
  }, []);

  const openNote = (path: string) => {
    if (embedded && onOpenNote) {
      onOpenNote(path);
      return;
    }
    sessionStorage.setItem('big-brain-open-note', path);
  };

  const NoteLink = ({ path, children }: { path: string; children: ReactNode }) =>
    embedded ? (
      <button type="button" className="link-btn" onClick={() => openNote(path)}>
        {children}
      </button>
    ) : (
      <Link to="/" onClick={() => openNote(path)}>
        {children}
      </Link>
    );

  if (!data) {
    return <p className="empty-state">Loading today...</p>;
  }

  return (
    <div className={`today-page${embedded ? ' embedded' : ''}`}>
      <header className="today-header">
        <h2>Today · {data.date}</h2>
        <p className="today-sub">
          {data.todayExchangeCount} Persona exchanges captured today
        </p>
      </header>

      <div className="today-grid">
        <section className="today-card">
          <h3>Today&apos;s chat log</h3>
          {data.todayChatPath ? (
            <NoteLink path={data.todayChatPath}>Open {data.todayChatPath}</NoteLink>
          ) : (
            <p className="muted">No chats captured yet today.</p>
          )}
        </section>

        <section className="today-card">
          <h3>Personas</h3>
          <ul className="panel-list compact">
            {data.personas.map((p) => (
              <li key={p.path}>
                <NoteLink path={p.path}>{p.title}</NoteLink>
              </li>
            ))}
            {data.personas.length === 0 && <li className="muted">No persona profiles yet</li>}
          </ul>
        </section>

        <section className="today-card wide">
          <h3>Recent notes</h3>
          <ul className="panel-list compact">
            {data.recentNotes.map((n) => (
              <li key={n.path}>
                <NoteLink path={n.path}>{n.title}</NoteLink>
                <span className="note-kind">{n.path.split('/')[0]}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="today-card">
          <h3>Recent chat days</h3>
          <ul className="panel-list compact">
            {data.recentChats.map((c) => (
              <li key={c.path}>
                <NoteLink path={c.path}>{c.title || c.path}</NoteLink>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
