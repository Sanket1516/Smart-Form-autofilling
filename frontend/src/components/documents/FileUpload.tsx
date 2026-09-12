import React, { useState, useRef, DragEvent, ChangeEvent } from 'react';
import { documentApi } from '../../services/api';
import { Button } from '../ui/Button';
import './FileUpload.css';

interface FileUploadProps {
  onUploadSuccess: (documentId: string) => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    setError(null);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    setError(null);
    if (e.target.files && e.target.files.length > 0) {
      await uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (file: File) => {
    // Basic validation
    if (file.type !== 'application/pdf') {
      setError('Only PDF files are currently supported.');
      return;
    }
    
    setIsUploading(true);
    setUploadProgress(0);
    
    try {
      // Simulate progress for UI (since fetch API doesn't easily expose upload progress)
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          const next = prev + 10;
          return next > 90 ? 90 : next;
        });
      }, 200);

      const response = await documentApi.uploadDocument(file);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      // Complete
      setTimeout(() => {
        setIsUploading(false);
        onUploadSuccess(response.document_id);
      }, 500);
    } catch (err: any) {
      setError(err.message || 'Failed to upload document');
      setIsUploading(false);
    }
  };

  const triggerFileInput = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <div className="file-upload-container">
      <div 
        className={`drop-zone ${isDragging ? 'dragging' : ''} ${error ? 'error' : ''}`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={triggerFileInput}
      >
        <input 
          type="file" 
          ref={fileInputRef} 
          onChange={handleFileChange} 
          accept="application/pdf"
          className="file-input-hidden"
        />
        
        <div className="drop-zone-content">
          {isUploading ? (
            <div className="upload-progress-container">
              <p>Uploading document...</p>
              <div className="progress-bar-bg">
                <div 
                  className="progress-bar-fill" 
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              <span>{uploadProgress}%</span>
            </div>
          ) : (
            <>
              <div className="upload-icon">📄</div>
              <h3>Drag and drop a PDF file here</h3>
              <p className="text-secondary">or click to browse from your computer</p>
              <Button type="button" variant="outline" className="mt-4">
                Select File
              </Button>
            </>
          )}
        </div>
      </div>
      
      {error && (
        <div className="upload-error-banner" role="alert">
          {error}
        </div>
      )}
    </div>
  );
};
