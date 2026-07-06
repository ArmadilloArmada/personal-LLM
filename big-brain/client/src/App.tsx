import { Routes, Route, NavLink } from 'react-router-dom';
import VaultPage from './pages/VaultPage';
import SettingsPage from './pages/SettingsPage';
import GraphPage from './pages/GraphPage';
import TodayPage from './pages/TodayPage';
import EmbedPage from './pages/EmbedPage';
import WorkflowListPage from './pages/WorkflowListPage';
import WorkflowEditorPage from './pages/WorkflowEditorPage';

const EMBEDDED = window.parent !== window;

function goToPersonaChat() {
  if (EMBEDDED) {
    window.parent.location.href = '/';
  } else {
    window.location.href = import.meta.env.VITE_PERSONA_URL ?? 'http://127.0.0.1:8765';
  }
}

export default function App() {
  return (
    <div className={`app-shell${EMBEDDED ? " embedded" : ""}`}>
      {!EMBEDDED && (
        <header className="top-bar">
          <h1>Big Brain</h1>
          <nav>
            <NavLink to="/today">Today</NavLink>
            <NavLink to="/" end>
              Vault
            </NavLink>
            <NavLink to="/graph">Graph</NavLink>
            <NavLink to="/workflows">Workflows</NavLink>
            <NavLink to="/settings">Settings</NavLink>
            <button type="button" className="nav-chat-btn" onClick={goToPersonaChat}>
              Chat
            </button>
          </nav>
        </header>
      )}
      <main className={`app-main${EMBEDDED ? " embedded" : ""}`}>
        <Routes>
          <Route path="/today" element={<TodayPage />} />
          <Route path="/" element={<VaultPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/embed" element={<EmbedPage />} />
          <Route path="/workflows" element={<WorkflowListPage />} />
          <Route path="/workflows/:id" element={<WorkflowEditorPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}
