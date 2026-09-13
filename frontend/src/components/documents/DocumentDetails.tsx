import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { documentApi, DocumentResponse } from '../../services/api';
import { ArrowLeft, FileText, CheckCircle, AlertCircle, Clock, Loader, Play, Tag } from 'lucide-react';
import { Button } from '../ui/Button';
import './DocumentDetails.css';

// ── helpers ────────────────────────────────────────────────────────────────

const CONCEPT_LABELS: Record<string, string> = {
  full_name: 'Full Name',
  first_name: 'First Name',
  middle_name: 'Middle Name',
  last_name: 'Last Name',
  date_of_birth: 'Date of Birth',
  gender: 'Gender',
  nationality: 'Nationality',
  email: 'Email',
  phone_number: 'Phone Number',
  linkedin: 'LinkedIn',
  github: 'GitHub',
  website: 'Website',
  current_address: 'Current Address',
  permanent_address: 'Permanent Address',
  address: 'Address',
  city: 'City',
  state: 'State',
  country: 'Country',
  postal_code: 'Postal Code',
  pan_number: 'PAN Number',
  passport_number: 'Passport Number',
  aadhaar_number: 'Aadhaar Number',
  university: 'University / College',
  degree: 'Degree',
  specialization: 'Specialization',
  graduation_year: 'Graduation Year',
  cgpa: 'CGPA / GPA',
  percentage: 'Percentage / Marks',
  organization: 'Company / Organization',
  job_title: 'Job Title / Designation',
  employment_dates: 'Employment Dates',
  work_experience: 'Work Experience',
  skills: 'Skills',
  certifications: 'Certifications',
  languages: 'Languages',
  education: 'Education',
  summary: 'Summary / Objective',
  achievements: 'Achievements',
};

const conceptLabel = (concept: string) =>
  CONCEPT_LABELS[concept] ?? concept.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

const confidenceColor = (c: number) => {
  if (c >= 0.9) return '#22c55e';
  if (c >= 0.7) return '#f59e0b';
  return '#ef4444';
};

// ── component ──────────────────────────────────────────────────────────────

export const DocumentDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [document, setDocument] = useState<DocumentResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processStatus, setProcessStatus] = useState<any>(null);
  const [facts, setFacts] = useState<any[]>([]);
  const [factsLoading, setFactsLoading] = useState(false);

  // Load document on mount
  useEffect(() => {
    if (id) fetchDocumentDetails(id);
  }, [id]);

  // Poll status while processing
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (document?.status === 'processing' || isProcessing) {
      interval = setInterval(() => {
        if (id) checkStatus(id);
      }, 3000);
    }
    return () => { if (interval) clearInterval(interval); };
  }, [document?.status, isProcessing, id]);

  // Fetch facts whenever the document reaches 'processed'
  useEffect(() => {
    if (document?.status === 'processed' && id) {
      fetchFacts(id);
    }
  }, [document?.status, id]);

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

  const fetchFacts = async (docId: string) => {
    setFactsLoading(true);
    try {
      const data = await documentApi.getDocumentFacts(docId);
      setFacts(data);
    } catch (err) {
      console.error('Failed to fetch document facts', err);
    } finally {
      setFactsLoading(false);
    }
  };

  const checkStatus = async (docId: string) => {
    try {
      const statusData = await documentApi.getDocumentStatus(docId);
      setProcessStatus(statusData);

      if (document && document.status !== statusData.status) {
        setDocument({ ...document, status: statusData.status });
        if (statusData.status === 'processed') {
          setIsProcessing(false);
          // Fetch facts immediately on the processing→processed transition
          fetchFacts(docId);
        } else if (statusData.status === 'failed') {
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
    setFacts([]); // clear stale facts from a previous run
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

  // ── loading / error states ──────────────────────────────────────────────

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

  // ── render ──────────────────────────────────────────────────────────────

  return (
    <div className="doc-details-container">
      <button className="back-btn" onClick={() => navigate('/documents')}>
        <ArrowLeft size={16} /> Back to Documents
      </button>

      {/* ── header ── */}
      <div className="doc-details-header">
        <div className="doc-title-section">
          <FileText size={32} className="doc-icon-large" />
          <div>
            <h2>{document.file_name}</h2>
            <p>Uploaded on {new Date(document.uploaded_at).toLocaleDateString()}</p>
          </div>
        </div>

        <div className="doc-actions">
          {(document.status === 'uploaded' || document.status === 'failed') && (
            <Button onClick={handleProcess} isLoading={isProcessing}>
              <Play size={16} style={{ marginRight: '8px' }} />
              {document.status === 'failed' ? 'Retry Processing' : 'Process Document'}
            </Button>
          )}
          {document.status === 'processed' && (
            <Button variant="outline" onClick={handleProcess} isLoading={isProcessing}>
              <Play size={16} style={{ marginRight: '8px' }} />
              Reprocess
            </Button>
          )}
          <Button variant="outline" onClick={handleDelete} className="btn-danger">
            Delete
          </Button>
        </div>
      </div>

      {/* ── processing status banner ── */}
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
                <p>
                  Information has been successfully extracted from this document.
                  {facts.length > 0 && ` ${facts.length} facts extracted below.`}
                </p>
              </div>
            </>
          )}

          {document.status === 'failed' && (
            <>
              <AlertCircle size={24} />
              <div>
                <h4>Processing Failed</h4>
                <p>{processStatus?.error || 'An error occurred while processing this document.'}</p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── document metadata grid ── */}
      <div className="doc-info-grid">
        <div className="info-card">
          <span className="info-label">Document Type</span>
          <span className="info-value">{document.document_type || 'Unknown'}</span>
        </div>
        <div className="info-card">
          <span className="info-label">Pages</span>
          <span className="info-value">{document.page_count ?? 'Unknown'}</span>
        </div>
        <div className="info-card">
          <span className="info-label">Upload Date</span>
          <span className="info-value">{new Date(document.uploaded_at).toLocaleString()}</span>
        </div>
        {document.processed_at && (
          <div className="info-card">
            <span className="info-label">Processed At</span>
            <span className="info-value">{new Date(document.processed_at).toLocaleString()}</span>
          </div>
        )}
      </div>

      {/* ── extracted information section ── */}
      {(document.status === 'processed' || facts.length > 0) && (
        <div className="doc-facts-section">
          <div className="doc-facts-header">
            <Tag size={20} />
            <h3>Extracted Information</h3>
            {factsLoading && <Loader size={16} className="spin" style={{ marginLeft: 8 }} />}
          </div>

          {factsLoading && facts.length === 0 ? (
            <div className="facts-loading">
              <Loader size={24} className="spin" />
              <p>Loading extracted facts...</p>
            </div>
          ) : facts.length === 0 ? (
            <div className="facts-empty">
              <p>No structured facts were extracted from this document. This may happen if the document is a scanned image without OCR support, or the content does not match any known field patterns.</p>
            </div>
          ) : (
            <div className="facts-grid-doc">
              {facts.map((fact: any, index: number) => (
                <div key={fact.fact_id || `${fact.concept}-${index}`} className="fact-card-doc">
                  <div className="fact-card-header">
                    <span className="fact-concept">{conceptLabel(fact.concept)}</span>
                    <span
                      className="fact-confidence"
                      style={{ color: confidenceColor(fact.confidence) }}
                      title={`Confidence: ${Math.round(fact.confidence * 100)}%`}
                    >
                      {Math.round(fact.confidence * 100)}%
                    </span>
                  </div>
                  <div className="fact-value">
                    {typeof fact.value === 'string' ? fact.value : JSON.stringify(fact.value)}
                  </div>
                  <div className="fact-meta">
                    Page {fact.source_page} &middot;{' '}
                    {fact.provenance?.extraction_method || 'extracted'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
