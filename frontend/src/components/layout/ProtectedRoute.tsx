import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { LoadingState } from '../ui/LoadingState';

export const ProtectedRoute = () => {
  const { user, isLoading } = useAuth();
  if (isLoading) return <LoadingState message="Loading…" fullScreen />;
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
};
