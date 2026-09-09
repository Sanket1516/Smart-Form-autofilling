import { useEffect, useState } from "react";
import { API_BASE_URL, getHealth } from "./services/api";

export default function App() {
  const [state, setState] = useState({ loading: true, health: null, error: null });

  async function refreshHealth() {
    setState({ loading: true, health: null, error: null });
    try {
      setState({ loading: false, health: await getHealth(), error: null });
    } catch (error) {
      setState({ loading: false, health: null, error: error.message });
    }
  }

  useEffect(() => {
    refreshHealth();
  }, []);

  return (
    <main className="shell">
      <section aria-labelledby="project-title" className="panel">
        <p className="eyebrow">Phase 1 foundation</p>
        <h1 id="project-title">Smart Form Auto-Filling System</h1>
        <p>
          The dashboard, document intelligence, and browser assistance will be introduced in later phases.
        </p>
        <div className="status" aria-live="polite">
          <h2>Service status</h2>
          <p>Backend: <strong>{state.loading ? "Checking…" : state.error ? "Unavailable" : "Healthy"}</strong></p>
          {state.health && <p>Version: {state.health.application_version}</p>}
          {state.error && <p className="error">{state.error}. Check that Docker services are running.</p>}
          <button type="button" onClick={refreshHealth} disabled={state.loading}>Refresh status</button>
        </div>
        <p className="endpoint">API endpoint: {API_BASE_URL}</p>
      </section>
    </main>
  );
}

