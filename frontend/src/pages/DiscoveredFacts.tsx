import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useLoader } from '../hooks/useLoader';
import { conceptLabel, documentApi, factsApi, formatValue } from '../services/api';
import { ErrorState } from '../components/ui/ErrorState';
import { LoadingState } from '../components/ui/LoadingState';
import { Confidence, OriginPill } from '../components/ui/Status';

export const DiscoveredFacts = () => {
  const { data, error, loading, reload } = useLoader(async () => {
    const [facts, documents] = await Promise.all([factsApi.discovered(), documentApi.list()]);
    return { facts, documents: documents.documents };
  });
  const [query, setQuery] = useState('');

  const names = useMemo(
    () => new Map((data?.documents ?? []).map((d) => [d.document_id, d.file_name])),
    [data],
  );
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return (data?.facts ?? []).filter((fact) =>
      !needle
      || fact.semantic_type.toLowerCase().includes(needle)
      || formatValue(fact.value).toLowerCase().includes(needle)
      || (fact.ontology ?? '').toLowerCase().includes(needle));
  }, [data, query]);

  if (loading && !data) return <LoadingState message="Loading extracted information…" />;
  if (error && !data) return <ErrorState message={error} onRetry={() => reload()} />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Discovered information</h1>
          <p className="muted">Everything found in your documents, including details that are not profile fields.</p>
        </div>
        <input className="text-input" type="search" placeholder="Filter…" aria-label="Filter discovered information"
          value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>
      <div className="card">
        {filtered.length === 0 ? (
          <p className="muted">{data?.facts.length ? 'Nothing matches the filter.' : 'Nothing has been extracted yet.'}</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Type</th><th>Value</th><th>Profile field</th><th>How</th><th>Document</th></tr></thead>
              <tbody>
                {filtered.map((fact) => (
                  <tr key={fact.id}>
                    <td className="tiny">{fact.semantic_type.replace(/_/g, ' ').toLowerCase()}</td>
                    <td>{formatValue(fact.value)}{fact.evidence_text && <div className="evidence">“{fact.evidence_text}”</div>}</td>
                    <td className="tiny">{fact.ontology ? conceptLabel(fact.ontology) : '—'}</td>
                    <td><OriginPill origin={fact.origin} /><div><Confidence value={fact.confidence} /></div></td>
                    <td className="tiny">
                      <Link to={`/documents/${fact.source_document_id}`}>{names.get(fact.source_document_id) ?? 'Document'}</Link>
                      {fact.source_page ? `, p.${fact.source_page}` : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
