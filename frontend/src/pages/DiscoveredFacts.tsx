import React, { useState, useEffect, useCallback } from 'react';
import {
  Brain, Search, Filter, RefreshCw, Tag, FileText,
  ChevronDown, ChevronRight, AlertTriangle, CheckCircle,
  Link as LinkIcon, X
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import './DiscoveredFacts.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface DiscoveredFact {
  id: string;
  field: string;
  semantic_type: string;
  value: string;
  data_type: string;
  confidence: number;
  entity_type?: string;
  entity_id?: string;
  evidence_text?: string;
  source_page?: number;
  ontology?: string;
  ontology_confidence?: number;
  document_type?: string;
  source_document_id?: string;
  conflict_status?: string;
  verification_status?: string;
  created_at?: string;
}

function confidenceColor(c: number): string {
  if (c >= 0.9) return 'conf-high';
  if (c >= 0.7) return 'conf-medium';
  return 'conf-low';
}

function confidenceLabel(c: number): string {
  if (c >= 0.9) return 'High';
  if (c >= 0.7) return 'Medium';
  return 'Low';
}

export const DiscoveredFacts = () => {
  const { token } = useAuth();
  const [facts, setFacts] = useState<DiscoveredFact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterDoc, setFilterDoc] = useState('');
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  const fetchFacts = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filterType) params.set('semantic_type', filterType);
      if (filterDoc) params.set('document_id', filterDoc);
      const url = `${API_BASE}/api/v1/profile/discovered-facts${params.toString() ? '?' + params : ''}`;
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setFacts(data.data || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [token, filterType, filterDoc]);

  useEffect(() => { fetchFacts(); }, [fetchFacts]);

  // Group by document_type → entity_type
  const grouped = facts.reduce<Record<string, Record<string, DiscoveredFact[]>>>((acc, fact) => {
    const docType = fact.document_type || 'UNKNOWN_DOCUMENT';
    const entityType = fact.entity_type || 'GENERAL';
    if (!acc[docType]) acc[docType] = {};
    if (!acc[docType][entityType]) acc[docType][entityType] = [];
    acc[docType][entityType].push(fact);
    return acc;
  }, {});

  const filtered = Object.entries(grouped).reduce<Record<string, Record<string, DiscoveredFact[]>>>((acc, [docType, entities]) => {
    const filteredEntities = Object.entries(entities).reduce<Record<string, DiscoveredFact[]>>((ea, [entityType, fcts]) => {
      const filteredFacts = fcts.filter(f =>
        !search ||
        f.field.toLowerCase().includes(search.toLowerCase()) ||
        f.semantic_type.toLowerCase().includes(search.toLowerCase()) ||
        String(f.value).toLowerCase().includes(search.toLowerCase())
      );
      if (filteredFacts.length > 0) ea[entityType] = filteredFacts;
      return ea;
    }, {});
    if (Object.keys(filteredEntities).length > 0) acc[docType] = filteredEntities;
    return acc;
  }, {});

  const toggleGroup = (key: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const totalFacts = facts.length;
  const conflictCount = facts.filter(f => f.conflict_status === 'CONFLICT').length;
  const verifiedCount = facts.filter(f => f.verification_status === 'VERIFIED').length;
  const uniqueTypes = new Set(facts.map(f => f.semantic_type)).size;

  return (
    <div className="discovered-facts-page">
      {/* Header */}
      <div className="page-header">
        <div className="page-title-section">
          <Brain size={28} className="page-icon" />
          <div>
            <h1>Discovered Facts</h1>
            <p>All information dynamically extracted from your documents by AI — without predefined rules.</p>
          </div>
        </div>
        <button className="btn-refresh" onClick={fetchFacts} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spinning' : ''} />
          Refresh
        </button>
      </div>

      {/* Stats Bar */}
      <div className="stats-row">
        <div className="stat-card">
          <span className="stat-value">{totalFacts}</span>
          <span className="stat-label">Total Facts</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{uniqueTypes}</span>
          <span className="stat-label">Semantic Types</span>
        </div>
        <div className="stat-card stat-conflict">
          <span className="stat-value">{conflictCount}</span>
          <span className="stat-label">Conflicts</span>
        </div>
        <div className="stat-card stat-verified">
          <span className="stat-value">{verifiedCount}</span>
          <span className="stat-label">Verified</span>
        </div>
      </div>

      {/* Filters */}
      <div className="filters-bar">
        <div className="search-box">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            placeholder="Search fields, types, values…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          {search && <button className="clear-btn" onClick={() => setSearch('')}><X size={14} /></button>}
        </div>
        <div className="filter-group">
          <Filter size={14} />
          <input
            type="text"
            placeholder="Filter by semantic type…"
            value={filterType}
            onChange={e => setFilterType(e.target.value)}
            className="filter-input"
          />
        </div>
        <div className="filter-group">
          <FileText size={14} />
          <input
            type="text"
            placeholder="Filter by document ID…"
            value={filterDoc}
            onChange={e => setFilterDoc(e.target.value)}
            className="filter-input"
          />
        </div>
      </div>

      {/* Content */}
      {error && (
        <div className="error-banner">
          <AlertTriangle size={16} /> {error}
        </div>
      )}

      {loading && (
        <div className="loading-state">
          <RefreshCw size={32} className="spinning" />
          <p>Loading discovered facts…</p>
        </div>
      )}

      {!loading && totalFacts === 0 && !error && (
        <div className="empty-state">
          <Brain size={48} className="empty-icon" />
          <h3>No Discovered Facts Yet</h3>
          <p>Upload documents to automatically extract information. The AI will discover fields without any predefined rules.</p>
        </div>
      )}

      {!loading && Object.entries(filtered).map(([docType, entities]) => (
        <div key={docType} className="doc-group">
          <button
            className="doc-group-header"
            onClick={() => toggleGroup(docType)}
          >
            <div className="doc-group-title">
              <FileText size={18} />
              <span className="doc-type-badge">{docType.replace(/_/g, ' ')}</span>
              <span className="group-count">
                {Object.values(entities).flat().length} facts
              </span>
            </div>
            {expandedGroups.has(docType) ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
          </button>

          {expandedGroups.has(docType) && (
            <div className="doc-group-body">
              {Object.entries(entities).map(([entityType, entityFacts]) => (
                <div key={entityType} className="entity-section">
                  <div className="entity-header">
                    <Tag size={14} />
                    <span className="entity-type-label">{entityType}</span>
                    <span className="entity-count">{entityFacts.length}</span>
                  </div>
                  <div className="facts-grid">
                    {entityFacts.map(fact => (
                      <div
                        key={fact.id}
                        className={`fact-card ${fact.conflict_status === 'CONFLICT' ? 'conflict' : ''} ${fact.verification_status === 'VERIFIED' ? 'verified' : ''}`}
                      >
                        <div className="fact-header">
                          <div className="fact-field">{fact.field}</div>
                          <div className="fact-badges">
                            {fact.conflict_status === 'CONFLICT' && (
                              <span className="badge badge-conflict">
                                <AlertTriangle size={10} /> Conflict
                              </span>
                            )}
                            {fact.verification_status === 'VERIFIED' && (
                              <span className="badge badge-verified">
                                <CheckCircle size={10} /> Verified
                              </span>
                            )}
                            <span className={`badge badge-conf ${confidenceColor(fact.confidence)}`}>
                              {confidenceLabel(fact.confidence)} ({Math.round(fact.confidence * 100)}%)
                            </span>
                          </div>
                        </div>

                        <div className="fact-semantic-type">{fact.semantic_type}</div>

                        <div className="fact-value">{String(fact.value)}</div>

                        {fact.evidence_text && (
                          <div className="fact-evidence">
                            <span className="evidence-label">Evidence:</span>
                            <span className="evidence-text">"{fact.evidence_text}"</span>
                            {fact.source_page && (
                              <span className="evidence-page">p.{fact.source_page}</span>
                            )}
                          </div>
                        )}

                        {fact.ontology && (
                          <div className="fact-ontology">
                            <LinkIcon size={11} />
                            <span>{fact.ontology}</span>
                            {fact.ontology_confidence && (
                              <span className="ontology-conf">
                                {Math.round(fact.ontology_confidence * 100)}%
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
