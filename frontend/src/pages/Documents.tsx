import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DocumentList } from '../components/documents/DocumentList';
import { DocumentUpload } from '../components/documents/DocumentUpload';
import { Button } from '../components/ui/Button';
import { FileText, Plus, X } from 'lucide-react';
import './Documents.css';

export const Documents = () => {
  const navigate = useNavigate();
  const [showUpload, setShowUpload] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUploadComplete = () => {
    setShowUpload(false);
    setRefreshTrigger(prev => prev + 1);
  };

  const handleViewDocument = (id: string) => {
    navigate(`/documents/${id}`);
  };

  return (
    <div className="documents-page">
      <div className="page-header">
        <div className="page-title-section">
          <FileText size={28} className="page-icon" />
          <div>
            <h1>Documents</h1>
            <p>Manage your uploaded documents and extract knowledge.</p>
          </div>
        </div>
        
        <Button 
          onClick={() => setShowUpload(!showUpload)}
          variant={showUpload ? "outline" : "primary"}
        >
          {showUpload ? (
            <><X size={16} style={{ marginRight: '8px' }} /> Cancel Upload</>
          ) : (
            <><Plus size={16} style={{ marginRight: '8px' }} /> Upload Document</>
          )}
        </Button>
      </div>

      <div className="page-content">
        {showUpload ? (
          <div className="upload-section">
            <DocumentUpload onUploadComplete={handleUploadComplete} />
          </div>
        ) : (
          <DocumentList 
            onViewDocument={handleViewDocument} 
            refreshTrigger={refreshTrigger} 
          />
        )}
      </div>
    </div>
  );
};
