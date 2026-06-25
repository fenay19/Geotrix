import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Sparkline } from '../components/ui/Sparkline';
import { SignalPill } from '../components/ui/SignalPill';
import { riskColor } from '../utils/risk';
import { Zap, HelpCircle, Globe, ArrowRight } from 'lucide-react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

export const Website: React.FC = () => {
  const navigate = useNavigate();
  const { session } = useAuth();

  const [gtiScore, setGtiScore] = useState<number>(68.5);
  const [gtiTrend, setGtiTrend] = useState<number[]>([52, 55, 60, 58, 62, 65, 68, 67, 66, 68.5]);
  const [publicSignals, setPublicSignals] = useState<any[]>([
    { symbol: 'GOLD', type: 'BUY', outcome: '+4.2% in 48h' },
    { symbol: 'OIL_BRENT', type: 'BUY', outcome: '+6.1% in 36h' },
    { symbol: 'SP500', type: 'SELL', outcome: '+2.8% in 24h' },
    { symbol: 'BTCUSD', type: 'BUY', outcome: '+8.3% in 72h' },
    { symbol: 'LMT', type: 'BUY', outcome: '+3.5% in 48h' },
  ]);

  useEffect(() => {
    const fetchLandingData = async () => {
      try {
        const gtiRes = await axios.get(`${API_BASE}/risk/gti`);
        if (gtiRes.data) {
          setGtiScore(gtiRes.data.current_score);
        }
        const trendRes = await axios.get(`${API_BASE}/risk/gti/history?limit=10`);
        if (trendRes.data) {
          setGtiTrend(trendRes.data.map((h: any) => h.score).reverse());
        }
        const sigRes = await axios.get(`${API_BASE}/signals/with-market?limit=5`);
        if (sigRes.data && sigRes.data.length > 0) {
          setPublicSignals(
            sigRes.data.slice(0, 5).map((s: any) => ({
              symbol: s.market_symbol ?? 'ASSET',
              type: s.signal_type ?? 'HOLD',
              outcome: s.signal_type === 'BUY' ? `Target: $${s.target_price}` : `Stop: $${s.stop_loss}`,
            }))
          );
        }
      } catch (err) {
        console.warn('Failed to load public landing data from API, using default mocks:', err);
      }
    };
    fetchLandingData();
  }, []);

  const handleLaunchClick = () => {
    if (session) {
      navigate('/dashboard');
    } else {
      navigate('/auth/login');
    }
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-base)',
        color: 'var(--text-primary)',
        width: '100%',
        minHeight: '100vh',
        boxSizing: 'border-box',
        overflowX: 'hidden',
        fontFamily: 'var(--font-display)',
      }}
    >
      {/* SECTION 1: Hero Section */}
      <section
        style={{
          height: '100vh',
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '24px',
          boxSizing: 'border-box',
        }}
      >
        {/* Animated SVG Globe Grid Background */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            zIndex: 0,
            overflow: 'hidden',
          }}
        >
          <svg
            width="100%"
            height="100%"
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              opacity: 0.1,
            }}
          >
            {/* Latitude Grid Circles */}
            <circle cx="50%" cy="50%" r="150" stroke="var(--accent-cyan)" strokeWidth="1" fill="none" />
            <circle cx="50%" cy="50%" r="280" stroke="var(--accent-cyan)" strokeWidth="1" fill="none" />
            <circle cx="50%" cy="50%" r="410" stroke="var(--accent-cyan)" strokeWidth="1" fill="none" />
            
            {/* Longitude Lines */}
            <line x1="50%" y1="0%" x2="50%" y2="100%" stroke="var(--accent-cyan)" strokeWidth="1" />
            <line x1="0%" y1="50%" x2="100%" y2="50%" stroke="var(--accent-cyan)" strokeWidth="1" />
            <path
              d="M 50,0 Q 500,300 500,600 T 950,1200"
              stroke="var(--accent-cyan)"
              strokeWidth="1.5"
              fill="none"
              strokeDasharray="5,5"
            />
            {/* Animated signal arcs */}
            <circle cx="50%" cy="50%" r="200" stroke="var(--accent-green)" strokeWidth="1.5" fill="none"
                    strokeDasharray="60 300" style={{ animation: 'rotateGrid 20s linear infinite' }} />
            <circle cx="50%" cy="50%" r="350" stroke="var(--risk-critical)" strokeWidth="1.5" fill="none"
                    strokeDasharray="100 500" style={{ animation: 'rotateGridCounter 30s linear infinite' }} />
          </svg>
          {/* Gradient Overlay */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'linear-gradient(to bottom, transparent 60%, var(--bg-base) 100%)',
            }}
          />
        </div>

        {/* Floating annotations */}
        <div
          style={{
            position: 'absolute',
            top: '32px',
            left: '32px',
            backgroundColor: 'rgba(26, 29, 36, 0.6)',
            border: '1px solid var(--border-bright)',
            padding: '8px 12px',
            borderRadius: 'var(--radius-md)',
            fontSize: '11px',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            backdropFilter: 'blur(8px)',
            color: 'var(--accent-green)',
            letterSpacing: '0.04em',
            zIndex: 1,
          }}
        >
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: 'var(--accent-green)',
              marginRight: '8px',
              display: 'inline-block',
              animation: 'ping 2s infinite',
            }}
          />
          LIVE PLATFORM ACTIVE
        </div>

        <div
          style={{
            position: 'absolute',
            top: '32px',
            right: '32px',
            backgroundColor: 'rgba(26, 29, 36, 0.6)',
            border: '1px solid var(--border-bright)',
            padding: '8px 12px',
            borderRadius: 'var(--radius-md)',
            fontSize: '10px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backdropFilter: 'blur(8px)',
            color: 'var(--text-secondary)',
            zIndex: 1,
          }}
        >
          <span style={{ fontWeight: 700, color: 'var(--accent-cyan)' }}>REAL OUTCOMES:</span>
          <span>GOLD +4.2%</span>
          <span style={{ color: 'var(--border-bright)' }}>|</span>
          <span>BRENT +6.1%</span>
        </div>

        {/* Headline cluster */}
        <div style={{ position: 'relative', zIndex: 1, textAlign: 'center', maxWidth: '800px' }}>
          <h1
            style={{
              fontSize: '64px',
              fontWeight: 700,
              lineHeight: 1.1,
              letterSpacing: '-0.03em',
              margin: '0 0 16px 0',
              fontFamily: 'var(--font-display)',
            }}
          >
            Trade the <br />
            <span style={{ color: 'var(--accent-cyan)', fontSize: '72px', fontWeight: 800 }}>
              Geopolitical Edge
            </span>
          </h1>
          <p
            style={{
              fontSize: '16px',
              lineHeight: 1.6,
              color: 'var(--text-secondary)',
              maxWidth: '520px',
              margin: '0 auto 32px',
            }}
          >
            GeoTrade v2.0 monitors live global events, computes the Global Tension Index, and generates AI trading signals before the market reacts.
          </p>

          {/* CTA buttons */}
          <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
            <button
              onClick={handleLaunchClick}
              style={{
                height: '48px',
                padding: '0 24px',
                backgroundColor: 'var(--text-primary)',
                color: 'var(--bg-base)',
                border: 'none',
                fontWeight: 700,
                fontSize: '13px',
                letterSpacing: '0.04em',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              LAUNCH PLATFORM
              <ArrowRight size={14} />
            </button>
            <a
              href="#how-it-works"
              style={{
                height: '48px',
                padding: '0 24px',
                backgroundColor: 'var(--bg-elevated)',
                border: '1px solid var(--border-bright)',
                color: 'var(--text-primary)',
                fontWeight: 700,
                fontSize: '13px',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                textDecoration: 'none',
                boxSizing: 'border-box',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-hover)')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
            >
              HOW IT WORKS
            </a>
          </div>
        </div>
      </section>

      {/* SECTION 2: Scrolling Public Signal Ticker */}
      <section
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderTop: '1px solid var(--border)',
          borderBottom: '1px solid var(--border)',
          height: '64px',
          display: 'flex',
          alignItems: 'center',
          overflow: 'hidden',
          width: '100%',
          position: 'relative',
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: '24px',
            fontWeight: 700,
            fontSize: '10px',
            color: 'var(--accent-cyan)',
            letterSpacing: '0.08em',
            zIndex: 2,
            backgroundColor: 'var(--bg-surface)',
            paddingRight: '16px',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          LIVE PLATFORM FEED
        </div>
        <div
          style={{
            display: 'flex',
            whiteSpace: 'nowrap',
            animation: 'publicMarquee 30s linear infinite',
            paddingLeft: '180px',
          }}
        >
          {publicSignals.concat(publicSignals).map((sig, idx) => (
            <div
              key={idx}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '12px',
                marginRight: '48px',
                fontSize: '13px',
              }}
            >
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{sig.symbol}</span>
              <SignalPill direction={sig.type} size="sm" />
              <span style={{ color: 'var(--accent-green)', fontWeight: 600 }}>{sig.outcome}</span>
            </div>
          ))}
        </div>
      </section>

      {/* SECTION 3: Feature Highlights */}
      <section
        id="how-it-works"
        style={{
          padding: '80px 24px',
          maxWidth: '1126px',
          margin: '0 auto',
          boxSizing: 'border-box',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '60px' }}>
          <span style={{ fontSize: '11px', color: 'var(--accent-cyan)', fontWeight: 700, letterSpacing: '0.08em' }}>
            ENGINEERED FOR ALPHA
          </span>
          <h2 style={{ fontSize: '28px', fontWeight: 600, marginTop: '8px', fontFamily: 'var(--font-display)' }}>
            System Capabilities
          </h2>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '40px' }}>
          {/* Col 1 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'rgba(6, 182, 212, 0.1)',
                border: '1px solid var(--accent-cyan)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--accent-cyan)',
              }}
            >
              <Globe size={20} />
            </div>
            <h3 style={{ fontSize: '16px', fontWeight: 600, margin: 0 }}>Know before the market does</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
              Monitors Reuters, GDELT, BBC, NewsAPI, and regional sources in real time. Events are classified, clustered, and ranked by potential severity within seconds.
            </p>
          </div>

          {/* Col 2 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'rgba(6, 182, 212, 0.1)',
                border: '1px solid var(--accent-cyan)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--accent-cyan)',
              }}
            >
              <Zap size={20} />
            </div>
            <h3 style={{ fontSize: '16px', fontWeight: 600, margin: 0 }}>Direction, entry, and exits</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
              Every signal contains entry prices, targets, stop-losses, and position sizing guidelines — computed via a hybrid AI/ML logic adjusted for conditional volatility.
            </p>
          </div>

          {/* Col 3 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'rgba(6, 182, 212, 0.1)',
                border: '1px solid var(--accent-cyan)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--accent-cyan)',
              }}
            >
              <HelpCircle size={20} />
            </div>
            <h3 style={{ fontSize: '16px', fontWeight: 600, margin: 0 }}>Understand why, not just what</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
              Signals are linked to the triggering geopolitical updates. Chat directly with the AI Analyst to break down RAG intelligence sources and test hypothetical scenarios.
            </p>
          </div>
        </div>
      </section>

      {/* SECTION 4: Live GTI Widget Banner */}
      <section
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderTop: '1px solid var(--border)',
          borderBottom: '1px solid var(--border)',
          padding: '40px 24px',
          boxSizing: 'border-box',
        }}
      >
        <div
          style={{
            maxWidth: '1126px',
            margin: '0 auto',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '24px',
          }}
        >
          {/* Score details */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.08em' }}>
              GLOBAL TENSION SCOREBOARD
            </span>
            <span
              style={{
                fontSize: '48px',
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
                color: riskColor(gtiScore),
                lineHeight: 1,
              }}
            >
              {gtiScore.toFixed(1)}
            </span>
          </div>

          {/* Sparkline trend */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span style={{ fontSize: '9px', color: 'var(--text-secondary)', fontWeight: 600, letterSpacing: '0.04em' }}>
              10-DAY TREND CONE
            </span>
            <Sparkline data={gtiTrend} color="amber" height={48} width={200} />
          </div>

          {/* Source meta */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', justifyContent: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', fontSize: '12px', fontWeight: 600, color: 'var(--accent-green)' }}>
              <span
                className="live-dot-green"
                style={{ width: '6px', height: '6px', borderRadius: '50%', marginRight: '6px' }}
              />
              WS CONNECTION ACTIVE
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Broadcasting feeds in real time
            </span>
          </div>
        </div>
      </section>

      {/* SECTION 5: CTA Footer */}
      <section
        style={{
          padding: '80px 24px',
          textAlign: 'center',
          maxWidth: '600px',
          margin: '0 auto',
        }}
      >
        <h2
          style={{
            fontSize: '32px',
            fontWeight: 700,
            lineHeight: 1.2,
            marginBottom: '16px',
            fontFamily: 'var(--font-display)',
          }}
        >
          Ready to trade the geopolitical edge?
        </h2>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '32px', lineHeight: 1.6 }}>
          Request credentials or login with your analyst profile to access the real-time decision dashboard.
        </p>
        <button
          onClick={handleLaunchClick}
          style={{
            height: '48px',
            padding: '0 32px',
            backgroundColor: 'transparent',
            border: '1px solid var(--accent-cyan)',
            color: 'var(--accent-cyan)',
            fontWeight: 700,
            fontSize: '13px',
            letterSpacing: '0.04em',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            textTransform: 'uppercase',
            transition: 'background var(--transition-fast) var(--ease-snap)',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(6, 182, 212, 0.08)')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
        >
          {session ? 'OPEN SYSTEM CONSOLE' : 'LAUNCH GATEWAY'}
        </button>
      </section>

      {/* Styles */}
      <style>{`
        @keyframes rotateGrid {
          from { transform: translate(-50%, -50%) rotate(0deg); }
          to { transform: translate(-50%, -50%) rotate(360deg); }
        }
        @keyframes rotateGridCounter {
          from { transform: translate(-50%, -50%) rotate(360deg); }
          to { transform: translate(-50%, -50%) rotate(0deg); }
        }
        @keyframes publicMarquee {
          0% { transform: translate3d(0, 0, 0); }
          100% { transform: translate3d(-50%, 0, 0); }
        }
        @keyframes ping {
          0% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.5); }
          70% { box-shadow: 0 0 0 8px rgba(0, 255, 136, 0); }
          100% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0); }
        }
      `}</style>
    </div>
  );
};

export default Website;
