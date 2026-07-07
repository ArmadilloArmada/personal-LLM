import { useEffect, useState } from 'react';
import GraphPage from './GraphPage';
import VaultPage from './VaultPage';
import TodayPage from './TodayPage';

type EmbedTab = 'graph' | 'vault' | 'today';

/** Minimal chrome for embedding in Persona iframe */
export default function EmbedPage() {
  const [tab, setTab] = useState<EmbedTab>('graph');
  const [vaultPath, setVaultPath] = useState<string | null>(null);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      const data = event.data;
      if (!data || typeof data !== 'object') return;
      if (data.type === 'persona-embed-tab') {
        if (data.tab === 'graph' || data.tab === 'vault' || data.tab === 'today') {
          setTab(data.tab);
        }
        if (data.path) {
          sessionStorage.setItem('big-brain-open-note', data.path);
          setVaultPath(data.path);
          setTab('vault');
        }
      }
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, []);

  const openVaultNote = (path: string) => {
    sessionStorage.setItem('big-brain-open-note', path);
    setVaultPath(path);
    setTab('vault');
  };

  return (
    <div className="embed-shell">
      <nav className="embed-tabs" aria-label="Big Brain views">
        <button
          type="button"
          className={tab === 'graph' ? 'active' : ''}
          onClick={() => setTab('graph')}
        >
          Graph
        </button>
        <button
          type="button"
          className={tab === 'vault' ? 'active' : ''}
          onClick={() => setTab('vault')}
        >
          Vault
        </button>
        <button
          type="button"
          className={tab === 'today' ? 'active' : ''}
          onClick={() => setTab('today')}
        >
          Today
        </button>
      </nav>
      <div className="embed-content">
        {tab === 'graph' && <GraphPage embedded onOpenNote={openVaultNote} />}
        {tab === 'vault' && <VaultPage embedded key={vaultPath ?? 'vault'} />}
        {tab === 'today' && <TodayPage embedded onOpenNote={openVaultNote} />}
      </div>
    </div>
  );
}
