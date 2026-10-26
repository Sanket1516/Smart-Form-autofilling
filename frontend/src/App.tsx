import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/layout/ProtectedRoute';
import { AppShell } from './components/layout/AppShell';

import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { Documents } from './pages/Documents';
import { DocumentDetails } from './components/documents/DocumentDetails';
import { Profile } from './pages/Profile';
import { DiscoveredFacts } from './pages/DiscoveredFacts';
import { Conflicts } from './pages/Conflicts';
import { Activity } from './pages/Activity';
import { Settings } from './pages/Settings';
import { Reviews } from './pages/Reviews';
import { Ask } from './pages/Ask';
import { DemoData } from './pages/DemoData';

const DEMO_ENABLED = import.meta.env.VITE_ENABLE_DEMO !== 'false';

// The landing page carries three.js and its own fonts; keep it out of the dashboard bundle.
const Landing = lazy(() => import('./landing/Landing'));
const landingFallback = <div style={{ minHeight: '100vh', background: '#07080a' }} aria-busy="true" />;

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<Suspense fallback={landingFallback}><Landing /></Suspense>} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected Routes inside AppShell */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/documents/:id" element={<DocumentDetails />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/discovered-facts" element={<DiscoveredFacts />} />
              <Route path="/conflicts" element={<Conflicts />} />
              <Route path="/reviews" element={<Reviews />} />
              <Route path="/ask" element={<Ask />} />
              {DEMO_ENABLED && <Route path="/demo-data" element={<DemoData />} />}
              <Route path="/activity" element={<Activity />} />
              <Route path="/settings" element={<Settings />} />
            </Route>
          </Route>

          {/* Catch all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
