import { useLoader } from '../hooks/useLoader';
import { conceptLabel, formatValue, formsApi, profileApi } from '../services/api';
import { ErrorState } from '../components/ui/ErrorState';
import { LoadingState } from '../components/ui/LoadingState';

const SESSION_STATUS: Record<string, { label: string; tone: string }> = {
  processing: { label: 'Analysing', tone: 'info' },
  ready: { label: 'Ready to fill', tone: 'info' },
  review_required: { label: 'Needs review', tone: 'warning' },
  information_required: { label: 'Missing information', tone: 'warning' },
  filled: { label: 'Filled', tone: 'success' },
  completed: { label: 'Submitted by you', tone: 'success' },
  closed: { label: 'Closed', tone: '' },
  failed: { label: 'Failed', tone: 'error' },
};

export const Activity = () => {
  const { data, error, loading, reload } = useLoader(async () => {
    const [sessions, corrections] = await Promise.all([formsApi.sessions(), profileApi.corrections()]);
    return { sessions, corrections };
  });
  if (loading && !data) return <LoadingState message="Loading activity…" />;
  if (error && !data) return <ErrorState message={error} onRetry={() => reload()} />;
  if (!data) return null;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Activity</h1>
          <p className="muted">Forms you filled with the extension and corrections you made to your profile.</p>
        </div>
      </div>
      <div className="card">
        <h2>Form sessions</h2>
        {data.sessions.length === 0 ? (
          <p className="muted">No forms filled yet. Use the browser extension on a form to start.</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Website</th><th>Started</th><th>Status</th><th>Fields</th><th>Filled</th><th>Failed</th></tr></thead>
              <tbody>
                {data.sessions.map((session) => {
                  const status = SESSION_STATUS[session.status] ?? { label: session.status, tone: '' };
                  return (
                    <tr key={session.session_id}>
                      <td title={session.page_url}>{session.website_origin}</td>
                      <td className="muted">{session.started_at ? new Date(session.started_at).toLocaleString() : '—'}</td>
                      <td><span className={`pill pill-${status.tone}`}>{status.label}</span></td>
                      <td>{session.total_fields}</td>
                      <td>{session.filled_fields}</td>
                      <td>{session.failed_fields}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <div className="card">
        <h2>Profile corrections</h2>
        {data.corrections.length === 0 ? (
          <p className="muted">No corrections yet.</p>
        ) : (
          <ul className="list">
            {data.corrections.map((correction) => (
              <li key={correction.correction_id} className="list-item">
                <div className="list-item-head">
                  <strong className="small">{conceptLabel(correction.concept)}</strong>
                  <span className="tiny muted">{new Date(correction.created_at).toLocaleString()}</span>
                </div>
                <p className="small no-margin">
                  {correction.original_value != null ? <><s>{formatValue(correction.original_value)}</s> → </> : null}
                  {correction.corrected_value != null ? formatValue(correction.corrected_value) : correction.reason}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
