import { Mark } from './Brand';
import './LoadingState.css';

interface LoadingStateProps {
  message?: string;
  fullScreen?: boolean;
}

export const LoadingState = ({ message = 'Loading…', fullScreen = false }: LoadingStateProps) => {
  return (
    <div className={`loading-state ${fullScreen ? 'full-screen' : ''}`} role="status" aria-live="polite">
      {fullScreen ? <Mark size={32} /> : <div className="spinner-large" aria-hidden="true" />}
      <p className="text-secondary">{message}</p>
    </div>
  );
};
