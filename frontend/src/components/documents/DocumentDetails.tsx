import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Download, Eye, RefreshCw, Trash2 } from 'lucide-react';
import { useLoader } from '../../hooks/useLoader';
import { conceptLabel, documentApi, documentTypeLabel, factsApi, formatValue, isRecord } from '../../services/api';
import { RecordTable } from './RecordTable';
import { Button } from '../ui/Button';
import { ErrorState } from '../ui/ErrorState';
import { LoadingState } from '../ui/LoadingState';
import { Confidence, DocumentStatusPill, IndexStatusPill, OriginPill } from '../ui/Status';

export const DocumentDetails = () => {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const { data, error, loading, reload } = useLoader(async () => {
    const document = await documentApi.get(id);
    const [facts, discovered] = document.status === 'processed'
      ? await Promise.all([documentApi.facts(id), factsApi.discovered(id)])
      : [[], []];
    return { document, facts, discovered };
  }, [id]);
  const [actionError, setActionError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);

  const processing = data?.document.status === 'processing';
  useEffect(() => {
    if (!processing) return;
    const timer = window.setInterval(() => void reload(true), 2000);
    return () => window.clearInterval(timer);
  }, [processing, reload]);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const act = async (action: () => Promise<void>) => {
    setBusy(true);
    setActionError(null);
    try {
      await action();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Action failed.');
    } finally {
      setBusy(false);
    }
  };

  if (loading && !data) return <LoadingState message="Loading document…" />;
  if (error && !data) return <ErrorState message={error} onRetry={() => reload()} />;
  if (!data) return null;
  const { document } = data;
  const facts = data.facts.filter((fact) => !isRecord(fact.value));
  const unmapped = data.discovered.filter((item) => !item.ontology);
  // subject marks, transactions and household members: one table per record type
  const records = new Map<string, Array<Record<string, unknown>>>();
  for (const item of data.discovered) {
    if (item.ontology && isRecord(item.value)) {
      records.set(item.ontology, [...(records.get(item.ontology) ?? []), item.value]);
    }
  }

  return (
    <div className="page">
      <Link to="/documents" className="small"><ArrowLeft size={14} /> All documents</Link>
      <div className="page-header">
        <div>
          <h1>{document.file_name}</h1>
          <div className="row">
            <DocumentStatusPill status={document.status} />
            {document.status === 'processed' && <IndexStatusPill status={document.index_status} />}
            {document.document_type && (
              <span className="pill" title={document.document_type_confidence ? `Identified with ${Math.round(document.document_type_confidence * 100)}% confidence` : undefined}>
                {documentTypeLabel(document.document_type)}
              </span>
            )}
            {document.page_count ? <span className="muted tiny">{document.page_count} page(s)</span> : null}
          </div>
        </div>
        <div className="toolbar">
          <Button variant="secondary" disabled={busy} onClick={() => act(async () => {
            if (previewUrl) URL.revokeObjectURL(previewUrl);
            setPreviewUrl(await documentApi.blobUrl(id, 'preview'));
          })}><Eye size={16} /> Preview</Button>
          <Button variant="secondary" disabled={busy} onClick={() => act(async () => {
            const url = await documentApi.blobUrl(id, 'download');
            const anchor = window.document.createElement('a');
            anchor.href = url;
            anchor.download = document.file_name;
            anchor.click();
            URL.revokeObjectURL(url);
          })}><Download size={16} /> Download</Button>
          <Button variant="secondary" disabled={busy || processing} onClick={() => act(async () => {
            await documentApi.reprocess(id);
            await reload(true);
          })}><RefreshCw size={16} /> Process again</Button>
          {confirmDelete ? (
            <>
              <Button variant="danger" disabled={busy} onClick={() => act(async () => {
                await documentApi.remove(id);
                navigate('/documents');
              })}>Delete permanently</Button>
              <Button variant="secondary" onClick={() => setConfirmDelete(false)}>Keep</Button>
            </>
          ) : (
            <Button variant="danger" onClick={() => setConfirmDelete(true)}><Trash2 size={16} /> Delete</Button>
          )}
        </div>
      </div>

      {actionError && <div className="alert alert-error" role="alert"><p>{actionError}</p></div>}
      {confirmDelete && (
        <div className="alert alert-warning" role="status">
          <p>Deleting removes the file and every fact and search entry extracted from it.</p>
        </div>
      )}

      {processing && (
        <div className="card" role="status">
          <p className="small">Processing: {document.current_stage ?? 'queued'}…</p>
          <div className="progress"><span style={{ width: `${document.progress}%` }} /></div>
        </div>
      )}
      {document.processing_error && (
        <div className={`alert ${document.status === 'failed' ? 'alert-error' : 'alert-warning'}`} role="alert">
          <p>{document.processing_error}</p>
        </div>
      )}
      {document.warnings.map((warning) => (
        <div key={warning} className="alert alert-warning"><p>{warning}</p></div>
      ))}
      {document.index_error && (
        <div className="alert alert-warning">
          <p>Search index: {document.index_error}. Extracted facts are still available.</p>
        </div>
      )}

      {previewUrl && (
        <div className="card">
          <div className="row"><h2 className="no-margin">Preview</h2><span className="spacer" />
            <button className="link-button" onClick={() => setPreviewUrl(null)}>Close</button></div>
          <iframe className="preview-frame" src={previewUrl} title={`Preview of ${document.file_name}`} sandbox="" />
        </div>
      )}

      {document.status === 'processed' && (
        <div className="card">
          <h2>Information found ({facts.length})</h2>
          {facts.length === 0 ? (
            <p className="muted">No profile information was found in this document.</p>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Field</th><th>Value</th><th>How</th><th>Evidence</th></tr></thead>
                <tbody>
                  {facts.map((fact) => (
                    <tr key={fact.fact_id}>
                      <td>{conceptLabel(fact.concept)}</td>
                      <td><strong>{formatValue(fact.value)}</strong>
                        {fact.raw_value != null && formatValue(fact.raw_value) !== formatValue(fact.value) && (
                          <div className="tiny muted">as written: {formatValue(fact.raw_value)}</div>
                        )}
                      </td>
                      <td>
                        <div className="row"><OriginPill origin={fact.origin} confirmed={fact.is_user_confirmed} /></div>
                        <Confidence value={fact.confidence} />
                      </td>
                      <td className="tiny muted">
                        {fact.source_page ? `Page ${fact.source_page}: ` : ''}{fact.evidence_text ?? ''}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="small muted" style={{ marginTop: '1rem' }}>
            Review and correct these values on <Link to="/profile">your profile</Link>.
          </p>
        </div>
      )}

      {[...records.entries()].map(([concept, rows]) => (
        <div className="card" key={concept}>
          <h2>{conceptLabel(concept)} ({rows.length})</h2>
          <RecordTable rows={rows} caption="Each row as printed on the document; amounts and marks normalised, references kept with leading zeros." />
        </div>
      ))}

      {unmapped.length > 0 && (
        <div className="card">
          <h2>Other details found ({unmapped.length})</h2>
          <p className="muted small">These details are kept for reference and document search but are not used as profile fields.</p>
          <ul className="list">
            {unmapped.slice(0, 50).map((item) => (
              <li key={item.id} className="list-item">
                <span className="tiny muted">{item.original_label ?? item.semantic_type.replace(/_/g, ' ').toLowerCase()}</span>
                <div>{formatValue(item.value)}</div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
