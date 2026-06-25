import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { LiveDot } from '../../components/ui/LiveDot';
import { SignalPill } from '../../components/ui/SignalPill';
import { riskColor } from '../../utils/risk';
import { Eye, EyeOff, Lock, Mail, Loader2 } from 'lucide-react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Live Preview States
  const [previewGti, setPreviewGti] = useState<number>(68.5);
  const [previewSignals, setPreviewSignals] = useState<any[]>([
    { symbol: 'GOLD', type: 'BUY', confidence: 88 },
    { symbol: 'OIL_BRENT', type: 'BUY', confidence: 85 },
    { symbol: 'SP500', type: 'SELL', confidence: 78 },
  ]);

  // Fetch live preview values from backend (non-auth public endpoints)
  useEffect(() => {
    const fetchPreviewData = async () => {
      try {
        const gtiRes = await axios.get(`${API_BASE}/risk/gti`);
        if (gtiRes.data) {
          setPreviewGti(gtiRes.data.current_score);
        }
        const sigRes = await axios.get(`${API_BASE}/signals/with-market?limit=3`);
        if (sigRes.data && sigRes.data.length > 0) {
          setPreviewSignals(
            sigRes.data.slice(0, 3).map((s: any) => ({
              symbol: s.market_symbol ?? 'ASSET',
              type: s.signal_type ?? 'HOLD',
              confidence: Math.round(s.confidence * 100),
            }))
          );
        }
      } catch (err) {
        console.warn('Failed to load public login preview data, using defaults:', err);
      }
    };
    fetchPreviewData();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const redirectUrl = new URLSearchParams(location.search).get('redirect') || '/dashboard';

    try {
      const params = new URLSearchParams();
      params.append('username', email);
      params.append('password', password);

      const res = await axios.post(`${API_BASE}/auth/login`, params, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      if (res.data && res.data.access_token) {
        // Fetch user info
        const token = res.data.access_token;
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        const userRes = await axios.get(`${API_BASE}/auth/me`);

        login(email, token, userRes.data);
        navigate(redirectUrl);
      } else {
        throw new Error('No access token returned');
      }
    } catch (err: any) {
      // Surface the real error from the backend (e.g. wrong credentials → 401)
      const detail = err?.response?.data?.detail;
      if (detail) {
        setError(detail);
      } else if (err?.response?.status === 401) {
        setError('Incorrect email or password. Please try again.');
      } else if (!err?.response) {
        setError('Cannot reach the server. Please check your connection and try again.');
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        minHeight: '100vh',
        width: '100%',
        backgroundColor: 'var(--bg-base)',
        color: 'var(--text-primary)',
        overflow: 'hidden',
      }}
    >
      {/* Left Panel: Auth Form */}
      <div
        style={{
          width: '440px',
          flexShrink: 0,
          backgroundColor: 'var(--bg-surface)',
          borderRight: '1px solid var(--border)',
          padding: '48px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          boxSizing: 'border-box',
        }}
      >
        {/* Logo Section */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <svg width="18" height="18" viewBox="0 0 15 15" fill="none">
              <path
                d="M1.5 7.5H3L4.5 12L7.5 3L9 9H10.5L12 6H13.5"
                stroke="var(--accent-green)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span
              style={{
                fontFamily: 'var(--font-display)',
                fontWeight: 700,
                fontSize: '15px',
                letterSpacing: '0.06em',
              }}
            >
              GEOTRADE
            </span>
          </div>
          <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.08em' }}>
            GEOPOLITICAL INTELLIGENCE & RISK STRATEGY
          </span>
        </div>

        {/* Form Body */}
        <div style={{ margin: '48px 0' }}>
          <h2 style={{ fontSize: '24px', fontWeight: 700, margin: '0 0 8px 0', fontFamily: 'var(--font-display)' }}>
            Sign in to your account
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '0 0 32px 0', lineHeight: 1.5 }}>
            Access live geopolitical signals, global threat indices, and logistics network simulations.
          </p>

          {error && (
            <div
              style={{
                padding: '10px 12px',
                border: '1px solid var(--risk-critical)',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'rgba(239, 68, 68, 0.08)',
                color: 'var(--risk-critical)',
                fontSize: '12px',
                marginBottom: '20px',
              }}
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Email Field */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  letterSpacing: '0.08em',
                  color: 'var(--text-secondary)',
                }}
              >
                EMAIL ADDRESS
              </label>
              <div style={{ position: 'relative' }}>
                <Mail
                  size={14}
                  style={{ position: 'absolute', left: '12px', top: '15px', color: 'var(--text-muted)' }}
                />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyst@geotrade.ai"
                  style={{
                    width: '100%',
                    height: '44px',
                    backgroundColor: 'var(--bg-base)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-md)',
                    padding: '0 12px 0 36px',
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-display)',
                    fontSize: '13px',
                    boxSizing: 'border-box',
                  }}
                />
              </div>
            </div>

            {/* Password Field */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label
                  style={{
                    fontSize: '10px',
                    fontWeight: 700,
                    letterSpacing: '0.08em',
                    color: 'var(--text-secondary)',
                  }}
                >
                  PASSWORD
                </label>
                <span
                  onClick={() => navigate('/auth/forgot-password')}
                  style={{
                    fontSize: '11px',
                    color: 'var(--accent-cyan)',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  Forgot password?
                </span>
              </div>
              <div style={{ position: 'relative' }}>
                <Lock
                  size={14}
                  style={{ position: 'absolute', left: '12px', top: '15px', color: 'var(--text-muted)' }}
                />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  style={{
                    width: '100%',
                    height: '44px',
                    backgroundColor: 'var(--bg-base)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-md)',
                    padding: '0 36px 0 36px',
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-display)',
                    fontSize: '13px',
                    boxSizing: 'border-box',
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '13px',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--text-muted)',
                    padding: 0,
                  }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                height: '48px',
                backgroundColor: 'transparent',
                border: '1px solid var(--accent-green)',
                color: 'var(--accent-green)',
                fontFamily: 'var(--font-display)',
                fontWeight: 700,
                fontSize: '13px',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                marginTop: '12px',
                transition: 'background var(--transition-fast) var(--ease-snap)',
              }}
              onMouseEnter={(e) => {
                if (!loading) e.currentTarget.style.backgroundColor = 'rgba(0, 255, 136, 0.08)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  AUTHENTICATING...
                </>
              ) : (
                'SIGN IN'
              )}
            </button>
          </form>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              margin: '24px 0',
              color: 'var(--text-muted)',
              fontSize: '11px',
              fontWeight: 600,
            }}
          >
            <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border)' }} />
            <span style={{ padding: '0 12px' }}>OR</span>
            <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border)' }} />
          </div>

          <button
            onClick={() => navigate('/auth/register')}
            style={{
              width: '100%',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-secondary)',
              fontSize: '13px',
              cursor: 'pointer',
              textAlign: 'center',
              fontWeight: 600,
            }}
            onMouseEnter={(e) => (e.currentTarget.style.textDecoration = 'underline')}
            onMouseLeave={(e) => (e.currentTarget.style.textDecoration = 'none')}
          >
            Don't have an account? Register user →
          </button>
        </div>

        {/* Footer */}
        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          © {new Date().getFullYear()} GeoTrade. All rights reserved. SECURE CONNECTION.
        </div>
      </div>

      {/* Right Panel: Live Platform Preview Overlay */}
      <div
        style={{
          flex: 1,
          position: 'relative',
          backgroundColor: '#0c0f14',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
        }}
      >
        {/* Mock background pattern representing UI elements (blurry) */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backgroundImage:
              'radial-gradient(circle at 20% 30%, rgba(6, 182, 212, 0.08) 0%, transparent 40%), radial-gradient(circle at 80% 70%, rgba(167, 139, 250, 0.08) 0%, transparent 40%)',
            filter: 'blur(30px)',
            zIndex: 0,
          }}
        />

        {/* Glass Preview Card */}
        <div
          style={{
            width: '340px',
            backgroundColor: 'rgba(26, 29, 36, 0.65)',
            border: '1px solid var(--border-bright)',
            borderRadius: 'var(--radius-lg)',
            padding: '24px',
            backdropFilter: 'blur(16px)',
            boxShadow: '0 20px 40px rgba(0, 0, 0, 0.4)',
            zIndex: 1,
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
            boxSizing: 'border-box',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span
              style={{
                fontSize: '10px',
                fontWeight: 700,
                color: 'var(--accent-cyan)',
                letterSpacing: '0.08em',
              }}
            >
              LIVE PLATFORM PREVIEW
            </span>
            <div style={{ display: 'flex', alignItems: 'center', fontSize: '11px', color: 'var(--text-muted)' }}>
              <LiveDot />
              Active
            </div>
          </div>

          {/* GTI score display */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'rgba(10, 11, 13, 0.4)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              padding: '12px 16px',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontWeight: 700 }}>GTI SCORE</span>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginTop: '2px' }}>
                GLOBAL TENSION
              </span>
            </div>
            <span
              style={{
                fontSize: '32px',
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
                color: riskColor(previewGti),
              }}
            >
              {previewGti.toFixed(1)}
            </span>
          </div>

          {/* Signal previews */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.04em' }}>
              RECENT TRADING OUTCOMES
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {previewSignals.map((sig, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    backgroundColor: 'rgba(10, 11, 13, 0.3)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '12px',
                  }}
                >
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{sig.symbol}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <SignalPill direction={sig.type} size="sm" />
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 600,
                        color: sig.type === 'BUY' ? 'var(--accent-green)' : 'var(--risk-critical)',
                      }}
                    >
                      {sig.confidence}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
