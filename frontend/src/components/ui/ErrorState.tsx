import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from './Button';
import './ErrorState.css';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  fullScreen?: boolean;
}

export const ErrorState = ({ title = 'Something went wrong', message, onRetry, fullScreen = false }: ErrorStateProps) => {
  return (
    <div className={`error-state ${fullScreen ? 'full-screen' : ''}`} role="alert">
      <span className="error-icon"><AlertCircle size={20} aria-hidden="true" /></span>
      <h3>{title}</h3>
      <p className="text-secondary">{message}</p>
      {onRetry && (
        <Button onClick={onRetry} variant="secondary">
          <RefreshCw size={14} aria-hidden="true" /> Try again
        </Button>
      )}
    </div>
  );
};
