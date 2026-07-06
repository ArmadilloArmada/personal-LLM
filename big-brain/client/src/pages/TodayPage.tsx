import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type TodayData } from '../lib/api';

export default function TodayPage() {
  const [data, setData] = useState<TodayData | null>(null);

  useEffect(() => {
    api.getToday().then(setData).catch(() => setData(null));
  }, []);

  if (!data) {
    return <p className="empty-state">Loading today...</p>;
  }

  return (
    <div className="today-page">
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
            <Link to="/" onClick={() => sessionStorage.setItem('big-brain-open-note', data.todayChatPath!)}>
              Open {data.todayChatPath}
            </Link>
          ) : (
            <p className="muted">No chats captured yet today.</p>
          )}
        </section>

        <section className="today-card">
          <h3>Personas</h3>
          <ul className="panel-list compact">
            {data.personas.map((p) => (
              <li key={p.path}>
                <Link to="/" onClick={() => sessionStorage.setItem('big-brain-open-note', p.path)}>
                  {p.title}
                </Link>
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
                <Link to="/" onClick={() => sessionStorage.setItem('big-brain-open-note', n.path)}>
                  {n.title}
                </Link>
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
                <Link to="/" onClick={() => sessionStorage.setItem('big-brain-open-note', c.path)}>
                  {c.title || c.path}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
