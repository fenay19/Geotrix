import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useWebSocket } from '../../context/WebSocketContext';
import { useGTI } from '../../hooks/useGTI';
import { riskColor, riskLabel } from '../../utils/risk';
import { LiveDot } from '../ui/LiveDot';
import {
  LayoutDashboard,
  Globe,
  BarChart2,
  Zap,
  Network,
  MessageSquare,
  LogOut,
  ChevronDown,
} from 'lucide-react';

export const Navigation: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { status, feedCount } = useWebSocket();
  const gti = useGTI();
  const [utcTime, setUtcTime] = useState<string>('00:00:00 UTC');
  const [dropdownOpen, setDropdownOpen] = useState<boolean>(false);
  const [windowWidth, setWindowWidth] = useState<number>(window.innerWidth);

  // Responsive width listener
  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // UTC Clock
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const hh = String(now.getUTCHours()).padStart(2, '0');
      const mm = String(now.getUTCMinutes()).padStart(2, '0');
      const ss = String(now.getUTCSeconds()).padStart(2, '0');
      setUtcTime(`${hh}:${mm}:${ss} UTC`);
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  // Keyboard Shortcuts (Alt + D/M/K/S/L/C)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.altKey && !e.ctrlKey && !e.metaKey) {
        const key = e.key.toLowerCase();
        switch (key) {
          case 'd':
            e.preventDefault();
            navigate('/dashboard');
            break;
          case 'm':
            e.preventDefault();
            navigate('/map');
            break;
          case 'k':
            e.preventDefault();
            navigate('/markets');
            break;
          case 's':
            e.preventDefault();
            navigate('/signals');
            break;
          case 'l':
            e.preventDefault();
            navigate('/supply-chain');
            break;
          case 'c':
            e.preventDefault();
            navigate('/chat');
            break;
          default:
            break;
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate]);

  const navItems = [
    { label: 'DASHBOARD', path: '/dashboard', icon: LayoutDashboard, key: 'D' },
    { label: 'MAP', path: '/map', icon: Globe, key: 'M' },
    { label: 'MARKETS', path: '/markets', icon: BarChart2, key: 'K' },
    { label: 'SIGNALS', path: '/signals', icon: Zap, key: 'S' },
    { label: 'SUPPLY CHAIN', path: '/supply-chain', icon: Network, key: 'L' },
    { label: 'CHAT', path: '/chat', icon: MessageSquare, key: 'C' },
  ];

  // User details fallback
  const userInitials = user?.name
    ? user.name.split(' ').map((n) => n[0]).join('').substring(0, 2).toUpperCase()
    : 'US';

  return (
    <header
      style={{
        height: '56px',
        width: '100%',
        backgroundColor: 'var(--bg-base)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        boxSizing: 'border-box',
      }}
    >
      {/* Left Cluster */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
        {/* Logo lockup */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', cursor: 'pointer' }} onClick={() => navigate('/')}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
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
                fontSize: '13px',
                color: 'var(--text-primary)',
                letterSpacing: '0.05em',
              }}
            >
              GEOTRADE
            </span>
          </div>
          <span
            style={{
              fontSize: '8px',
              fontFamily: 'var(--font-display)',
              color: 'var(--text-muted)',
              fontWeight: 600,
              letterSpacing: '0.1em',
              marginTop: '1px',
            }}
          >
            TRADER V2.0
          </span>
        </div>

        {/* GTI Readout */}
        {gti && windowWidth >= 960 && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              borderLeft: '1px solid var(--border)',
              paddingLeft: '20px',
            }}
          >
            {windowWidth >= 1280 && (
              <span
                style={{
                  fontSize: '10px',
                  color: 'var(--text-muted)',
                  fontWeight: 700,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  lineHeight: 1.1,
                }}
              >
                GLOBAL TENSION
                <br />
                INDEX
              </span>
            )}
            <span
              style={{
                fontSize: '24px',
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
                color: riskColor(gti.score),
                lineHeight: 1,
              }}
            >
              {gti.score.toFixed(1)}
            </span>
            {windowWidth >= 1280 && (
              <span
                style={{
                  fontSize: '12px',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600,
                  color: gti.delta > 0 ? 'var(--risk-critical)' : 'var(--accent-green)',
                }}
              >
                {gti.delta > 0 ? `+${gti.delta}` : gti.delta} {gti.delta > 0 ? '↗' : '↘'}
              </span>
            )}
            <span
              style={{
                fontSize: '9px',
                fontFamily: 'var(--font-display)',
                fontWeight: 700,
                color: riskColor(gti.score),
                backgroundColor: 'var(--bg-elevated)',
                border: `1px solid ${riskColor(gti.score)}`,
                borderRadius: 'var(--radius-sm)',
                padding: '2px 6px',
                lineHeight: 1,
              }}
            >
              {riskLabel(gti.score)}
            </span>
          </div>
        )}
      </div>

      {/* Center Cluster — Nav Tabs */}
      <nav
        style={{
          display: 'flex',
          height: '100%',
          alignItems: 'center',
          gap: windowWidth >= 1280 ? '16px' : '4px',
        }}
      >
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          const Icon = item.icon;
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              style={{
                background: 'transparent',
                border: 'none',
                borderBottom: isActive ? '2px solid var(--accent-cyan)' : '2px solid transparent',
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                padding: '0 8px',
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer',
                fontFamily: 'var(--font-display)',
                fontSize: '12px',
                fontWeight: 600,
                transition: 'all var(--transition-fast) var(--ease-snap)',
              }}
            >
              <Icon size={14} style={{ color: isActive ? 'var(--accent-cyan)' : 'inherit' }} />
              {windowWidth >= 960 ? (
                <>
                  <span>{item.label}</span>
                  {windowWidth >= 1280 && (
                    <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontWeight: 400 }}>
                      ⌥{item.key}
                    </span>
                  )}
                </>
              ) : null}
            </button>
          );
        })}
      </nav>

      {/* Right Cluster */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Live Indicator */}
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <LiveDot status={status === 'connected' ? 'live' : status === 'reconnecting' ? 'degraded' : 'offline'} />
          {windowWidth >= 960 && (
            <span
              style={{
                fontSize: '10px',
                fontWeight: 700,
                color: 'var(--text-secondary)',
                letterSpacing: '0.04em',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {status === 'connected' && `LIVE · ${feedCount} FEEDS`}
              {status === 'reconnecting' && 'RECONNECTING...'}
              {status === 'disconnected' && 'OFFLINE'}
            </span>
          )}
        </div>

        {/* UTC Clock */}
        {windowWidth >= 960 && (
          <span
            style={{
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--text-secondary)',
              borderLeft: '1px solid var(--border)',
              paddingLeft: '16px',
            }}
          >
            {utcTime}
          </span>
        )}

        {/* User avatar pill */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-bright)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              height: '32px',
              padding: '0 8px',
              borderRadius: 'var(--radius-lg)',
              cursor: 'pointer',
              color: 'var(--text-primary)',
            }}
          >
            <div
              style={{
                width: '20px',
                height: '20px',
                borderRadius: '50%',
                backgroundColor: 'rgba(6, 182, 212, 0.15)',
                border: '1px solid var(--accent-cyan)',
                color: 'var(--accent-cyan)',
                fontSize: '10px',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {userInitials}
            </div>
            <ChevronDown size={12} style={{ color: 'var(--text-muted)' }} />
          </button>

          {/* Dropdown Menu */}
          {dropdownOpen && (
            <>
              <div
                onClick={() => setDropdownOpen(false)}
                style={{ position: 'fixed', inset: 0, zIndex: 101 }}
              />
              <div
                style={{
                  position: 'absolute',
                  right: 0,
                  top: '38px',
                  width: '180px',
                  backgroundColor: 'var(--bg-elevated)',
                  border: '1px solid var(--border-bright)',
                  borderRadius: 'var(--radius-md)',
                  padding: '4px',
                  boxShadow: 'var(--shadow)',
                  zIndex: 102,
                }}
              >
                <div style={{ padding: '8px', borderBottom: '1px solid var(--border)', marginBottom: '4px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {user?.name || 'Session Active'}
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '2px', wordBreak: 'break-all' }}>
                    {user?.email || 'analyst@geotrade.ai'}
                  </div>
                </div>
                <button
                  onClick={async () => {
                    setDropdownOpen(false);
                    await logout();
                    navigate('/auth/login');
                  }}
                  style={{
                    width: '100%',
                    background: 'transparent',
                    border: 'none',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '8px',
                    color: 'var(--accent-red)',
                    fontSize: '12px',
                    fontWeight: 600,
                    textAlign: 'left',
                    cursor: 'pointer',
                    borderRadius: 'var(--radius-sm)',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.08)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <LogOut size={13} />
                  SIGN OUT
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
};

export default Navigation;
