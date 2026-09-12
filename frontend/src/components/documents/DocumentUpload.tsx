import React, { useCallback, useState } from 'react';
import { Upload, X, File, AlertCircle, CheckCircle } from 'lucide-react';
import { Button } from '../ui/Button';
import { documentApi } from '../../services/api';
import './DocumentUpload.css';

interface DocumentUploadProps {
  onUploadComplete?: () => void;
}

export const DocumentUpload: React.FC<DocumentUploadProps> = ({ onUploadComplete }) => {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      validateAndSetFile(droppedFile);
    }
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (selectedFile: File) => {
    setError(null);
    setSuccess(false);
    if (selectedFile.type !== "application/pdf") {
      setError("Please upload a PDF file.");
      return;
    }
    // Limit to 10MB
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError("File is too large. Maximum size is 10MB.");
      return;
    }
    setFile(selectedFile);
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setIsUploading(true);
    setError(null);
    setSuccess(false);
    
    try {
      await documentApi.uploadDocument(file);
      setSuccess(true);
      setFile(null);
      if (onUploadComplete) {
        onUploadComplete();
      }
    } catch (err: any) {
      setError(err.message || 'Upload failed. Document could not be processed.');
    } finally {
      setIsUploading(false);
    }
  };

  const clearFile = () => {
    setFile(null);
    setError(null);
    setSuccess(false);
  };

  return (
    <div className="document-upload-container">
      {error && (
        <div className="upload-alert error">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}
      
      {success && (
        <div className="upload-alert success">
          <CheckCircle size={20} />
          <span>Document uploaded successfully!</span>
        </div>
      )}

      {!file ? (
        <form 
          className={`upload-dropzone ${dragActive ? 'active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input 
            type="file" 
            id="file-upload" 
            multiple={false} 
            accept=".pdf,application/pdf"
            onChange={handleChange} 
            className="hidden-input"
          />
          <label htmlFor="file-upload" className="upload-label">
            <div className="upload-content">
              <Upload size={48} className="upload-icon" />
              <h3>Drag & Drop Document</h3>
              <p>or</p>
              <span className="browse-btn">Choose File</span>
              <p className="supported-text">Supported: PDF (Max 10MB)</p>
            </div>
          </label>
        </form>
      ) : (
        <div className="selected-file-card">
          <div className="file-info">
            <File size={32} className="file-icon" />
            <div className="file-details">
              <h4>{file.name}</h4>
              <p>{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
            </div>
          </div>
          <button className="clear-btn" onClick={clearFile} disabled={isUploading} aria-label="Remove file">
            <X size={20} />
          </button>
          
          <div className="upload-actions">
            <Button 
              onClick={handleUpload} 
              isLoading={isUploading}
              fullWidth
            >
              Upload Document
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
