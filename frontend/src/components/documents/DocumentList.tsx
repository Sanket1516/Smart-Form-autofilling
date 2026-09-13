import React, { useEffect, useState } from 'react';
import { documentApi, DocumentResponse } from '../../services/api';
import { File, Trash2, Clock, CheckCircle, AlertCircle, Loader, Download, Eye } from 'lucide-react';
import { Button } from '../ui/Button';
import './DocumentList.css';

interface DocumentListProps {
  onViewDocument: (id: string) => void;
  refreshTrigger?: number; // Used to trigger refresh from parent
}

export const DocumentList: React.FC<DocumentListProps> = ({ onViewDocument, refreshTrigger = 0 }) => {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDocuments();
  }, [refreshTrigger]);

  const fetchDocuments = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await documentApi.getDocuments();
      setDocuments(data);
    } catch (err: any) {
      setError('Failed to load documents. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation(); // Prevent triggering row click
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    
    try {
      await documentApi.deleteDocument(id);
      setDocuments(prev => prev.filter(doc => doc.document_id !== id));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete document';
      if (message === 'Document not found') {
        setDocuments(prev => prev.filter(doc => doc.document_id !== id));
        return;
      }
      setError(message);
    }
  };

  const handleDownload = async (e: React.MouseEvent, doc: DocumentResponse) => {
    e.stopPropagation();
    try {
      await documentApi.downloadDocument(doc.document_id, doc.file_name);
    } catch (err: any) {
      alert(err?.message || 'Failed to download file');
    }
  };

  const handlePreview = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    onViewDocument(id);
  };

  const renderStatus = (status: string) => {
    switch (status.toLowerCase()) {
      case 'processed':
        return (
          <span className="doc-status processed">
            <CheckCircle size={14} /> Processed
          </span>
        );
      case 'processing':
        return (
          <span className="doc-status processing">
            <Loader size={14} className="spin" /> Processing
          </span>
        );
      case 'failed':
        return (
          <span className="doc-status failed">
            <AlertCircle size={14} /> Failed
          </span>
        );
      default:
        return (
          <span className="doc-status uploaded">
            <Clock size={14} /> Uploaded
          </span>
        );
    }
  };

  if (isLoading) {
    return (
      <div className="doc-list-loading">
        <Loader className="spin" size={32} />
        <p>Loading documents...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="doc-list-error">
        <AlertCircle size={32} />
        <p>{error}</p>
        <Button onClick={fetchDocuments} variant="outline">Retry</Button>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="doc-list-empty">
        <File size={48} className="empty-icon" />
        <h3>No documents yet</h3>
        <p>Upload a document to start extracting information.</p>
      </div>
    );
  }

  return (
    <div className="doc-list-container">
      <div className="doc-grid">
        {documents.map((doc) => (
          <div 
            key={doc.document_id} 
            className="doc-card"
            onClick={() => onViewDocument(doc.document_id)}
          >
            <div className="doc-card-header">
              <File className="doc-icon" size={24} />
              <div className="doc-actions-inline" onClick={(e) => e.stopPropagation()}>
                <button 
                  className="doc-action-btn" 
                  onClick={(e) => handlePreview(e, doc.document_id)}
                  aria-label="Preview document"
                  title="Preview / Details"
                >
                  <Eye size={16} />
                </button>
                <button 
                  className="doc-action-btn" 
                  onClick={(e) => handleDownload(e, doc)}
                  aria-label="Download document"
                  title="Download file"
                >
                  <Download size={16} />
                </button>
                <button 
                  className="doc-delete-btn" 
                  onClick={(e) => handleDelete(e, doc.document_id)}
                  aria-label="Delete document"
                  title="Delete"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
            
            <div className="doc-card-body">
              <h4 className="doc-name" title={doc.file_name}>{doc.file_name}</h4>
              <p className="doc-date">
                {new Date(doc.uploaded_at).toLocaleDateString(undefined, { 
                  year: 'numeric', month: 'short', day: 'numeric' 
                })}
              </p>
            </div>
            
            <div className="doc-card-footer">
              {renderStatus(doc.status)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
