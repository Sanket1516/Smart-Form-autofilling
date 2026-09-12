import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from './Button';
import './ErrorState.css';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  fullScreen?: boolean;
}

export const ErrorState = ({ title = 'An error occurred', message, onRetry, fullScreen = false }: ErrorStateProps) => {
  return (
    <div className={`error-state ${fullScreen ? 'full-screen' : ''}`} role="alert">
      <AlertTriangle className="error-icon" size={48} />
      <h3>{title}</h3>
      <p className="text-secondary">{message}</p>
      {onRetry && (
        <Button onClick={onRetry} variant="secondary">
          Try Again
        </Button>
      )}
    </div>
  );
};
