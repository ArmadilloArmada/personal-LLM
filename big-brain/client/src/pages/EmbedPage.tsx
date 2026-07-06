import GraphPage from './GraphPage';

/** Minimal chrome for embedding in Persona iframe */
export default function EmbedPage() {
  return (
    <div className="embed-shell">
      <GraphPage embedded />
    </div>
  );
}
