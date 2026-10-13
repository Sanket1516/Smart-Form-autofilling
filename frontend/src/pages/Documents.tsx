import { useEffect, useRef, useState, type DragEvent } from 'react';
import { Link } from 'react-router-dom';
import { Trash2, UploadCloud } from 'lucide-react';
import { useLoader } from '../hooks/useLoader';
import { documentApi, type DocumentData } from '../services/api';
import { Button } from '../components/ui/Button';
import { ErrorState } from '../components/ui/ErrorState';
import { LoadingState } from '../components/ui/LoadingState';
import { DocumentStatusPill, IndexStatusPill } from '../components/ui/Status';
import { ACCEPTED, MAX_MB, validateFile } from '../services/files';

export const Documents = () => {
  const { data, error, loading, reload } = useLoader(() => documentApi.list().then((d) => d.documents));
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const processing = data?.some((doc) => doc.status === 'processing') ?? false;
  useEffect(() => {
    if (!processing) return;
    const timer = window.setInterval(() => void reload(true), 2000);
    return () => window.clearInterval(timer);
  }, [processing, reload]);

  const upload = async (file: File | undefined) => {
    if (!file) return;
    setUploadError(null);
    setNotice(null);
    const problem = validateFile(file);
    if (problem) {
      setUploadError(problem);
      return;
    }
    setUploading(true);
    try {
      const document = await documentApi.upload(file);
      setNotice(`${document.file_name} uploaded. Processing has started.`);
      await reload(true);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed.');
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    void upload(event.dataTransfer.files[0]);
  };

  const remove = async (doc: DocumentData) => {
    setUploadError(null);
    try {
      await documentApi.remove(doc.document_id);
      setConfirmDelete(null);
      setNotice(`${doc.file_name} and the information extracted from it were deleted.`);
      await reload(true);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Delete failed.');
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Documents</h1>
          <p className="muted">Upload documents to build your profile. Files stay private to your account.</p>
        </div>
      </div>

      <div
        className={`dropzone ${dragging ? 'active' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <UploadCloud size={36} className="muted" aria-hidden="true" />
        <p>Drag a file here, or</p>
        <Button onClick={() => inputRef.current?.click()} isLoading={uploading}>Choose a file</Button>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          hidden
          aria-label="Upload document"
          onChange={(e) => void upload(e.target.files?.[0])}
        />
        <p className="muted tiny" style={{ marginTop: '0.75rem' }}>
          PDF, DOCX, TXT, PNG or JPG · up to {MAX_MB} MB. Scanned documents need the optional OCR engine.
        </p>
      </div>

      {uploadError && <div className="alert alert-error" role="alert"><p>{uploadError}</p></div>}
      {notice && <div className="alert alert-success" role="status"><p>{notice}</p></div>}

      <div className="card">
        <h2>Your documents</h2>
        {loading && !data && <LoadingState message="Loading documents…" />}
        {error && !data && <ErrorState message={error} onRetry={() => reload()} />}
        {data && data.length === 0 && <div className="empty"><p>No documents uploaded yet.</p></div>}
        {data && data.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>Name</th><th>Status</th><th>Facts</th><th>Search</th><th>Uploaded</th><th /></tr>
              </thead>
              <tbody>
                {data.map((doc) => (
                  <tr key={doc.document_id}>
                    <td>
                      <Link to={`/documents/${doc.document_id}`}>{doc.file_name}</Link>
                      {doc.processing_error && <div className="tiny" style={{ color: 'var(--color-error)' }}>{doc.processing_error}</div>}
                      {doc.status === 'processing' && (
                        <div className="progress" aria-label={`Processing ${doc.progress}%`}>
                          <span style={{ width: `${doc.progress}%` }} />
                        </div>
                      )}
                    </td>
                    <td><DocumentStatusPill status={doc.status} /></td>
                    <td>{doc.status === 'processed' ? doc.fact_count : '—'}</td>
                    <td>{doc.status === 'processed' ? <IndexStatusPill status={doc.index_status} /> : '—'}</td>
                    <td className="muted">{new Date(doc.uploaded_at).toLocaleString()}</td>
                    <td>
                      {confirmDelete === doc.document_id ? (
                        <span className="row">
                          <Button variant="danger" onClick={() => void remove(doc)}>Delete</Button>
                          <Button variant="secondary" onClick={() => setConfirmDelete(null)}>Keep</Button>
                        </span>
                      ) : (
                        <button className="link-button danger" onClick={() => setConfirmDelete(doc.document_id)}
                          aria-label={`Delete ${doc.file_name}`}>
                          <Trash2 size={16} />
                        </button>
                      )}
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
