import React from 'react';
import { Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Navigation from '../components/shell/Navigation';
import StatusBar from '../components/shell/StatusBar';

// Public pages
import Website from '../pages/Website';

// Auth pages
import Login from '../pages/auth/Login';
import ForgotPassword from '../pages/auth/ForgotPassword';
import ResetPassword from '../pages/auth/ResetPassword';
import Register from '../pages/auth/Register';

// Protected pages
import Dashboard from '../pages/Dashboard';
import Map from '../pages/Map';
import Markets from '../pages/Markets';
import Signals from '../pages/Signals';
import SupplyChain from '../pages/SupplyChain';
import AiChat from '../pages/AiChat';

// AuthGuard component
export const AuthGuard: React.FC = () => {
  const { session, loading } = useAuth();

  if (loading) {
    return (
      <div
        style={{
          height: '100vh',
          width: '100vw',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'var(--bg-base)',
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-display)',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="animate-spin"
            style={{ color: 'var(--accent-cyan)' }}
          >
            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
          </svg>
          <span
            style={{
              fontSize: '10px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: 'var(--text-secondary)',
            }}
          >
            VALIDATING GEOTRADE KEY CORES
          </span>
        </div>
      </div>
    );
  }

  if (!session) {
    const currentPath = window.location.pathname + window.location.search;
    return <Navigate to={`/auth/login?redirect=${encodeURIComponent(currentPath)}`} replace />;
  }

  return <Outlet />;
};

// AppShell layout wrapper
export const AppShell: React.FC = () => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        backgroundColor: 'var(--bg-base)',
        color: 'var(--text-primary)',
        overflow: 'hidden',
        boxSizing: 'border-box',
      }}
    >
      <Navigation />
      <main style={{ flex: 1, overflow: 'hidden', width: '100%', position: 'relative' }}>
        <Outlet />
      </main>
      <StatusBar />
    </div>
  );
};

export const AppRouter: React.FC = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<Website />} />
      
      {/* Auth Routes */}
      <Route path="/auth/login" element={<Login />} />
      <Route path="/auth/forgot-password" element={<ForgotPassword />} />
      <Route path="/auth/reset-password" element={<ResetPassword />} />
      <Route path="/auth/register" element={<Register />} />

      {/* Protected Routes (Wrapped in AuthGuard & AppShell layout) */}
      <Route element={<AuthGuard />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/map" element={<Map />} />
          <Route path="/markets" element={<Markets />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/supply-chain" element={<SupplyChain />} />
          <Route path="/chat" element={<AiChat />} />
        </Route>
      </Route>

      {/* Catch-all fallback redirect */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default AppRouter;
