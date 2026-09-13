import React, { useState, useEffect, useCallback } from 'react';
import {
  AlertTriangle, RefreshCw, CheckCircle, XCircle,
  Edit3, ChevronRight, FileText, Layers, Info
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import './Conflicts.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface Candidate {
  value: string;
  document_id?: string;
  page?: number;
  confidence?: number;
  evidence?: string;
}

interface Conflict {
  id: string;
  field: string;
  semantic_type: string;
  ontology?: string;
  conflict_type?: string;
  conflict_status?: string;
  candidates: Candidate[];
  created_at?: string;
}

type ResolutionType = 'candidate_a' | 'candidate_b' | 'custom' | 'reject' | null;

interface ResolvedState {
  [conflictId: string]: {
    resolution: ResolutionType;
    customValue?: string;
    resolvedValue?: string;
  };
}

export const Conflicts = () => {
  const { token } = useAuth();
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resolving, setResolving] = useState<string | null>(null);
  const [customValues, setCustomValues] = useState<Record<string, string>>({});
  const [resolved, setResolved] = useState<ResolvedState>({});
  const [showResolved, setShowResolved] = useState(false);

  const fetchConflicts = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/profile/facts/conflicts`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setConflicts(data.data || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchConflicts(); }, [fetchConflicts]);

  const resolve = async (conflictId: string, resolution: Exclude<ResolutionType, null>) => {
    if (!token) return;
    setResolving(conflictId);
    try {
      const body: any = { resolution };
      if (resolution === 'custom') {
        body.custom_value = customValues[conflictId] || '';
      }
      const res = await fetch(`${API_BASE}/api/v1/profile/facts/conflicts/${conflictId}/resolve`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Determine resolved value for display
      const conflict = conflicts.find(c => c.id === conflictId);
      let resolvedValue = '';
      if (resolution === 'candidate_a') resolvedValue = conflict?.candidates[0]?.value || '';
      else if (resolution === 'candidate_b') resolvedValue = conflict?.candidates[1]?.value || '';
      else if (resolution === 'custom') resolvedValue = customValues[conflictId] || '';
      else resolvedValue = '— Rejected —';

      setResolved(prev => ({
        ...prev,
        [conflictId]: { resolution, resolvedValue }
      }));
    } catch (e: any) {
      setError(`Failed to resolve: ${e.message}`);
    } finally {
      setResolving(null);
    }
  };

  const activeConflicts = conflicts.filter(c => !resolved[c.id]);
  const resolvedConflicts = conflicts.filter(c => resolved[c.id]);

  return (
    <div className="conflicts-page">
      {/* Header */}
      <div className="page-header">
        <div className="page-title-section">
          <AlertTriangle size={28} className="page-icon conflict-icon" />
          <div>
            <h1>Extraction Conflicts</h1>
            <p>Review and resolve conflicting information found across your documents.</p>
          </div>
        </div>
        <div className="header-actions">
          {resolvedConflicts.length > 0 && (
            <button
              className="btn-toggle-resolved"
              onClick={() => setShowResolved(p => !p)}
            >
              {showResolved ? 'Hide Resolved' : `Show Resolved (${resolvedConflicts.length})`}
            </button>
          )}
          <button className="btn-refresh" onClick={fetchConflicts} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spinning' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Info Banner */}
      <div className="info-banner">
        <Info size={16} />
        <div>
          <strong>Human-in-the-Loop Review:</strong> These conflicts were detected when AI extracted contradictory values
          from your documents. Select the correct value, enter a custom one, or reject the field.
          Your decision is stored with <code>verification_status = VERIFIED</code>.
        </div>
      </div>

      {/* Stats */}
      <div className="conflict-stats">
        <div className={`conflict-stat ${activeConflicts.length > 0 ? 'active' : ''}`}>
          <span className="cstat-num">{activeConflicts.length}</span>
          <span className="cstat-label">Pending</span>
        </div>
        <div className="conflict-stat resolved-stat">
          <span className="cstat-num">{resolvedConflicts.length}</span>
          <span className="cstat-label">Resolved</span>
        </div>
        <div className="conflict-stat">
          <span className="cstat-num">{conflicts.length}</span>
          <span className="cstat-label">Total</span>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <AlertTriangle size={16} /> {error}
        </div>
      )}

      {loading && (
        <div className="loading-state">
          <RefreshCw size={32} className="spinning" />
          <p>Loading conflicts…</p>
        </div>
      )}

      {!loading && activeConflicts.length === 0 && resolvedConflicts.length === 0 && !error && (
        <div className="empty-state">
          <CheckCircle size={48} className="empty-icon-success" />
          <h3>No Conflicts Found</h3>
          <p>All extracted information is consistent across your documents. Upload more documents to detect cross-document conflicts.</p>
        </div>
      )}

      {!loading && activeConflicts.length === 0 && resolvedConflicts.length > 0 && !showResolved && (
        <div className="all-resolved-banner">
          <CheckCircle size={20} />
          All conflicts have been resolved!
        </div>
      )}

      {/* Active Conflicts */}
      {!loading && activeConflicts.map(conflict => (
        <ConflictCard
          key={conflict.id}
          conflict={conflict}
          customValue={customValues[conflict.id] || ''}
          onCustomValueChange={val => setCustomValues(prev => ({ ...prev, [conflict.id]: val }))}
          onResolve={resolution => resolve(conflict.id, resolution)}
          isResolving={resolving === conflict.id}
        />
      ))}

      {/* Resolved Conflicts (optional) */}
      {showResolved && resolvedConflicts.map(conflict => {
        const r = resolved[conflict.id];
        return (
          <div key={conflict.id} className="conflict-card resolved-card">
            <div className="conflict-card-header">
              <div className="conflict-meta">
                <CheckCircle size={18} className="resolved-icon" />
                <span className="conflict-field">{conflict.field}</span>
                <span className="semantic-badge">{conflict.semantic_type}</span>
                {conflict.ontology && (
                  <span className="ontology-badge">{conflict.ontology}</span>
                )}
              </div>
              <span className="resolved-label">Resolved: {r.resolution}</span>
            </div>
            <div className="resolved-value">
              Final value: <strong>{r.resolvedValue}</strong>
            </div>
          </div>
        );
      })}
    </div>
  );
};

/* ─── ConflictCard sub-component ─── */
function ConflictCard({
  conflict,
  customValue,
  onCustomValueChange,
  onResolve,
  isResolving
}: {
  conflict: Conflict;
  customValue: string;
  onCustomValueChange: (v: string) => void;
  onResolve: (r: Exclude<ResolutionType, null>) => void;
  isResolving: boolean;
}) {
  const [showCustom, setShowCustom] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState<'a' | 'b' | null>(null);
  const [selectedCustom, setSelectedCustom] = useState(false);

  const candA = conflict.candidates[0];
  const candB = conflict.candidates[1];

  const handleSubmit = () => {
    if (selectedCandidate === 'a') onResolve('candidate_a');
    else if (selectedCandidate === 'b') onResolve('candidate_b');
    else if (selectedCustom && customValue.trim()) onResolve('custom');
  };

  return (
    <div className="conflict-card">
      {/* Card Header */}
      <div className="conflict-card-header">
        <div className="conflict-meta">
          <AlertTriangle size={16} className="conflict-icon-sm" />
          <span className="conflict-field">{conflict.field}</span>
          <span className="semantic-badge">{conflict.semantic_type}</span>
          {conflict.ontology && (
            <span className="ontology-badge">{conflict.ontology}</span>
          )}
          {conflict.conflict_type && (
            <span className={`type-badge type-${conflict.conflict_type.toLowerCase()}`}>
              {conflict.conflict_type.replace(/_/g, ' ')}
            </span>
          )}
        </div>
        <div className="conflict-actions-top">
          <button
            className="btn-reject"
            onClick={() => onResolve('reject')}
            disabled={isResolving}
            title="Reject this field — don't use any value"
          >
            <XCircle size={14} /> Reject
          </button>
        </div>
      </div>

      {/* Candidates */}
      <div className="candidates-grid">
        {candA && (
          <button
            className={`candidate-card ${selectedCandidate === 'a' ? 'selected' : ''}`}
            onClick={() => { setSelectedCandidate('a'); setSelectedCustom(false); }}
            disabled={isResolving}
          >
            <div className="candidate-label">
              <span className="candidate-letter">A</span>
              {selectedCandidate === 'a' && <CheckCircle size={14} className="selected-icon" />}
            </div>
            <div className="candidate-value">{candA.value}</div>
            {candA.evidence && (
              <div className="candidate-evidence">
                <ChevronRight size={11} />
                <span>"{candA.evidence}"</span>
              </div>
            )}
            <div className="candidate-meta">
              {candA.page && <span><FileText size={11} /> p.{candA.page}</span>}
              {candA.confidence !== undefined && (
                <span><Layers size={11} /> {Math.round(candA.confidence * 100)}%</span>
              )}
              {candA.document_id && (
                <span className="doc-ref">{candA.document_id.slice(-8)}</span>
              )}
            </div>
          </button>
        )}

        {candB && (
          <button
            className={`candidate-card ${selectedCandidate === 'b' ? 'selected' : ''}`}
            onClick={() => { setSelectedCandidate('b'); setSelectedCustom(false); }}
            disabled={isResolving}
          >
            <div className="candidate-label">
              <span className="candidate-letter">B</span>
              {selectedCandidate === 'b' && <CheckCircle size={14} className="selected-icon" />}
            </div>
            <div className="candidate-value">{candB.value}</div>
            {candB.evidence && (
              <div className="candidate-evidence">
                <ChevronRight size={11} />
                <span>"{candB.evidence}"</span>
              </div>
            )}
            <div className="candidate-meta">
              {candB.page && <span><FileText size={11} /> p.{candB.page}</span>}
              {candB.confidence !== undefined && (
                <span><Layers size={11} /> {Math.round(candB.confidence * 100)}%</span>
              )}
              {candB.document_id && (
                <span className="doc-ref">{candB.document_id.slice(-8)}</span>
              )}
            </div>
          </button>
        )}

        <button
          className={`candidate-card custom-card ${selectedCustom ? 'selected' : ''}`}
          onClick={() => { setSelectedCustom(true); setSelectedCandidate(null); setShowCustom(true); }}
          disabled={isResolving}
        >
          <div className="candidate-label">
            <Edit3 size={14} />
            <span className="candidate-letter-text">Custom</span>
            {selectedCustom && <CheckCircle size={14} className="selected-icon" />}
          </div>
          <div className="candidate-value custom-placeholder">Enter your own value</div>
          {(showCustom || selectedCustom) && (
            <input
              className="custom-input"
              type="text"
              placeholder="Type correct value…"
              value={customValue}
              onChange={e => { e.stopPropagation(); onCustomValueChange(e.target.value); }}
              onClick={e => e.stopPropagation()}
              autoFocus
            />
          )}
        </button>
      </div>

      {/* Confirm button */}
      <div className="conflict-footer">
        <button
          className="btn-confirm"
          onClick={handleSubmit}
          disabled={isResolving || (!selectedCandidate && (!selectedCustom || !customValue.trim()))}
        >
          {isResolving ? (
            <><RefreshCw size={14} className="spinning" /> Resolving…</>
          ) : (
            <><CheckCircle size={14} /> Confirm Selection</>
          )}
        </button>
      </div>
    </div>
  );
}
