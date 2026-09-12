import React from 'react';
import './LoadingState.css';

interface LoadingStateProps {
  message?: string;
  fullScreen?: boolean;
}

export const LoadingState = ({ message = 'Loading...', fullScreen = false }: LoadingStateProps) => {
  return (
    <div className={`loading-state ${fullScreen ? 'full-screen' : ''}`} role="status" aria-live="polite">
      <div className="spinner-large"></div>
      <p className="text-secondary">{message}</p>
    </div>
  );
};
