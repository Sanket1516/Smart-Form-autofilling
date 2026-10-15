import { Link, useNavigate } from 'react-router-dom';
import { AlertTriangle, FileQuestion, FileText, Puzzle, UserCheck } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useLoader } from '../hooks/useLoader';
import { documentApi, factsApi, profileApi, reviewsApi } from '../services/api';
import { Button } from '../components/ui/Button';
import { ErrorState } from '../components/ui/ErrorState';
import { LoadingState } from '../components/ui/LoadingState';
import { DocumentStatusPill } from '../components/ui/Status';

export const Dashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data, error, loading, reload } = useLoader(async () => {
    const [documents, profile, conflicts, reviews] = await Promise.all([
      documentApi.list(),
      profileApi.get(),
      factsApi.conflicts(),
      reviewsApi.pending(),
    ]);
    return { documents: documents.documents, profile, conflicts, reviews };
  });

  if (loading && !data) return <LoadingState message="Loading your overview…" />;
  if (error && !data) return <ErrorState message={error} onRetry={() => reload()} />;
  if (!data) return null;

  const processing = data.documents.filter((d) => d.status === 'processing').length;
  const needsAttention = data.documents.filter((d) => d.status === 'failed' || d.status === 'requires_review').length;
  const resolved = data.profile.fields.filter((f) => f.status !== 'conflict').length;
  const confirmed = data.profile.fields.filter((f) => f.is_user_confirmed).length;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <span className="eyebrow">Overview</span>
          <h1>Hello{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}</h1>
          <p className="muted">Your documents, profile and form-filling activity at a glance.</p>
        </div>
        <div className="toolbar">
          <Button onClick={() => navigate('/documents')}><FileText size={16} /> Upload a document</Button>
        </div>
      </div>

      <div className="grid grid-4">
        <div className="card stat">
          <span className="muted small"><FileText size={14} /> Documents</span>
          <span className="stat-number">{data.documents.length}</span>
          <span className="muted tiny">
            {processing ? `${processing} processing` : 'none processing'}
            {needsAttention ? ` · ${needsAttention} need attention` : ''}
          </span>
        </div>
        <div className="card stat">
          <span className="muted small"><UserCheck size={14} /> Profile values</span>
          <span className="stat-number">{resolved}</span>
          <span className="muted tiny">{confirmed} confirmed by you</span>
        </div>
        <div className="card stat">
          <span className="muted small"><AlertTriangle size={14} /> Conflicts</span>
          <span className="stat-number">{data.conflicts.length}</span>
          <Link className="tiny" to="/conflicts">{data.conflicts.length ? 'Resolve conflicts' : 'Nothing to resolve'}</Link>
        </div>
        <div className="card stat">
          <span className="muted small"><FileQuestion size={14} /> Field reviews</span>
          <span className="stat-number">{data.reviews.length}</span>
          <Link className="tiny" to="/reviews">{data.reviews.length ? 'Review pending fields' : 'Nothing pending'}</Link>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <h2>Recent documents</h2>
          {data.documents.length === 0 ? (
            <div className="empty">
              <h3>No documents yet</h3>
              <p>Upload a résumé, certificate or ID document to build your profile.</p>
              <Button onClick={() => navigate('/documents')}>Upload a document</Button>
            </div>
          ) : (
            <ul className="list">
              {data.documents.slice(0, 5).map((doc) => (
                <li key={doc.document_id} className="list-item list-item-head">
                  <Link to={`/documents/${doc.document_id}`}>{doc.file_name}</Link>
                  <span className="row">
                    <span className="muted tiny">{doc.fact_count} facts</span>
                    <DocumentStatusPill status={doc.status} />
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="card">
          <h2><Puzzle size={18} /> Fill a form with the browser extension</h2>
          <ol className="steps small">
            <li>Load the extension from <code>extension/dist</code> (see the README).</li>
            <li>Open the form you want to fill and click the Smart Form icon. The form is detected automatically.</li>
            <li>Choose <strong>Analyze this form</strong> to match its fields with your profile.</li>
            <li>Check every suggestion, fix anything that is wrong, then choose <strong>Fill</strong> for the fields you approve.</li>
            <li>Review the page and submit the form yourself.</li>
          </ol>
          <Link to="/profile" className="small">Check your profile values first</Link>
        </div>
      </div>
    </div>
  );
};
