import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { documentApi, DocumentResponse } from '../../services/api';
import { ArrowLeft, FileText, CheckCircle, AlertCircle, Clock, Loader, Play } from 'lucide-react';
import { Button } from '../ui/Button';
import './DocumentDetails.css';

export const DocumentDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [document, setDocument] = useState<DocumentResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processStatus, setProcessStatus] = useState<any>(null);

  useEffect(() => {
    if (id) {
      fetchDocumentDetails(id);
    }
  }, [id]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (document?.status === 'processing' || isProcessing) {
      interval = setInterval(() => {
        if (id) checkStatus(id);
      }, 3000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [document?.status, isProcessing, id]);

  const fetchDocumentDetails = async (docId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await documentApi.getDocument(docId);
      setDocument(data);
      if (data.status === 'processing') {
        checkStatus(docId);
      }
    } catch (err: any) {
      setError('Failed to load document details.');
    } finally {
      setIsLoading(false);
    }
  };

  const checkStatus = async (docId: string) => {
    try {
      const statusData = await documentApi.getDocumentStatus(docId);
      setProcessStatus(statusData);
      
      // Update main document status if it changed
      if (document && document.status !== statusData.status) {
        setDocument({ ...document, status: statusData.status });
        if (statusData.status === 'processed' || statusData.status === 'failed') {
          setIsProcessing(false);
        }
      }
    } catch (err) {
      console.error('Failed to fetch status', err);
    }
  };

  const handleProcess = async () => {
    if (!id || !document) return;
    
    setIsProcessing(true);
    try {
      await documentApi.processDocument(id);
      setDocument({ ...document, status: 'processing' });
      setProcessStatus({ status: 'processing', progress: 0, current_stage: 'Starting' });
    } catch (err) {
      alert('Failed to start processing');
      setIsProcessing(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    
    try {
      await documentApi.deleteDocument(id);
      navigate('/documents');
    } catch (err) {
      alert('Failed to delete document');
    }
  };

  if (isLoading) {
    return (
      <div className="doc-details-loading">
        <Loader className="spin" size={32} />
        <p>Loading document details...</p>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="doc-details-error">
        <AlertCircle size={32} />
        <h2>Document not found</h2>
        <p>{error || 'The document you are looking for does not exist.'}</p>
        <Button onClick={() => navigate('/documents')}>Back to Documents</Button>
      </div>
    );
  }

  return (
    <div className="doc-details-container">
      <button className="back-btn" onClick={() => navigate('/documents')}>
        <ArrowLeft size={16} /> Back to Documents
      </button>

      <div className="doc-details-header">
        <div className="doc-title-section">
          <FileText size={32} className="doc-icon-large" />
          <div>
            <h2>{document.file_name}</h2>
            <p>Uploaded on {new Date(document.uploaded_at).toLocaleDateString()}</p>
          </div>
        </div>
        
        <div className="doc-actions">
          {document.status === 'uploaded' && (
            <Button onClick={handleProcess} isLoading={isProcessing}>
              <Play size={16} style={{ marginRight: '8px' }} />
              Process Document
            </Button>
          )}
          <Button variant="outline" onClick={handleDelete} className="btn-danger">
            Delete
          </Button>
        </div>
      </div>

      <div className="doc-status-section">
        <h3>Processing Status</h3>
        
        <div className={`status-banner ${document.status}`}>
          {document.status === 'uploaded' && (
            <>
              <Clock size={24} />
              <div>
                <h4>Ready for processing</h4>
                <p>This document has been uploaded but not yet processed. Processing extracts facts that can be used for auto-filling.</p>
              </div>
            </>
          )}
          
          {(document.status === 'processing' || isProcessing) && (
            <>
              <Loader size={24} className="spin" />
              <div className="processing-progress">
                <h4>Processing document...</h4>
                <p>{processStatus?.current_stage || 'Initializing pipeline...'}</p>
                {processStatus?.progress !== undefined && (
                  <div className="progress-bar-container">
                    <div 
                      className="progress-bar-fill" 
                      style={{ width: `${processStatus.progress}%` }}
                    />
                  </div>
                )}
              </div>
            </>
          )}
          
          {document.status === 'processed' && (
            <>
              <CheckCircle size={24} />
              <div>
                <h4>Processing Complete</h4>
                <p>Information has been successfully extracted from this document.</p>
              </div>
            </>
          )}
          
          {document.status === 'failed' && (
            <>
              <AlertCircle size={24} />
              <div>
                <h4>Processing Failed</h4>
                <p>{processStatus?.error || 'An error occurred while processing this document.'}</p>
                <Button variant="outline" size="sm" onClick={handleProcess}>Try Again</Button>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="doc-info-grid">
        <div className="info-card">
          <span className="info-label">File Type</span>
          <span className="info-value">{document.document_type || 'PDF'}</span>
        </div>
        <div className="info-card">
          <span className="info-label">Pages</span>
          <span className="info-value">{document.page_count || 'Unknown'}</span>
        </div>
        <div className="info-card">
          <span className="info-label">Upload Date</span>
          <span className="info-value">{new Date(document.uploaded_at).toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
};
