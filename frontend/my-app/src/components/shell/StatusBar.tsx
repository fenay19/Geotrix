import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGTI } from '../../hooks/useGTI';
import { useAlerts } from '../../hooks/useAlerts';
import { riskColor } from '../../utils/risk';
import { SeverityBadge } from '../ui/SeverityBadge';
import { formatRelativeTime } from '../../utils/format';
import { AlertTriangle, X, Bell } from 'lucide-react';

export const StatusBar: React.FC = () => {
  const navigate = useNavigate();
  const gti = useGTI();
  const { alerts } = useAlerts(6); // Alert on severity >= 6
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);

  const currentScore = gti?.score ?? 68.5;
  const trend = gti?.trend ?? [55, 60, 58, 62, 65, 68, 67, 66, 68, 69, 70, 68.5];

  // Helper to generate tooltip title for squares
  const getSquareLabel = (index: number, score: number) => {
    const hoursAgo = 11 - index;
    return hoursAgo === 0 ? `Current: ${score}` : `${hoursAgo}h ago: ${score}`;
  };

  const handleAlertClick = (countryId: number | undefined) => {
    if (countryId) {
      navigate(`/map?country=${countryId}&view=2d`);
      setDrawerOpen(false);
    } else {
      navigate('/map');
    }
  };

  return (
    <>
      <footer
        style={{
          height: '48px',
          width: '100%',
          backgroundColor: 'var(--bg-elevated)',
          borderTop: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          position: 'fixed',
          bottom: 0,
          left: 0,
          zIndex: 99,
          boxSizing: 'border-box',
        }}
      >
        {/* Left Zone: GTI Trend Grid */}
        <div
          style={{
            width: '240px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            borderRight: '1px solid var(--border)',
            height: '100%',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span
              style={{
                fontSize: '9px',
                color: 'var(--text-muted)',
                fontWeight: 700,
                letterSpacing: '0.08em',
              }}
            >
              GTI TREND
            </span>
            <span
              style={{
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
                color: riskColor(currentScore),
              }}
            >
              {currentScore.toFixed(1)}
            </span>
          </div>
          {/* 12 small squares */}
          <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
            {trend.slice(-12).map((score, idx) => (
              <div
                key={idx}
                title={getSquareLabel(idx, score)}
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '1px',
                  backgroundColor: riskColor(score),
                  cursor: 'pointer',
                  opacity: 0.85,
                  transition: 'transform 150ms var(--ease-snap)',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.3)')}
                onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
              />
            ))}
          </div>
        </div>

        {/* Center Zone: Horizontal Scrolling Alert Cards Ticker */}
        <div
          style={{
            flex: 1,
            overflow: 'hidden',
            height: '100%',
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <div
            className="ticker-container"
            style={{
              display: 'flex',
              whiteSpace: 'nowrap',
              position: 'absolute',
              willChange: 'transform',
            }}
            onMouseEnter={(e) => {
              const el = e.currentTarget as HTMLElement;
              el.style.animationPlayState = 'paused';
            }}
            onMouseLeave={(e) => {
              const el = e.currentTarget as HTMLElement;
              el.style.animationPlayState = 'running';
            }}
          >
            {/* Seamless scrolling marquee containing active alerts */}
            <div
              style={{
                display: 'flex',
                animation: 'marquee-scroll 205s linear infinite',
              }}
            >
              {(alerts.length > 0 ? alerts : []).map((alert) => (
                <div
                  key={`feed-1-${alert.id}`}
                  onClick={() => handleAlertClick(alert.country_id)}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    width: '320px',
                    height: '28px',
                    backgroundColor: 'var(--bg-surface)',
                    borderLeft: `3px solid ${riskColor(alert.severity * 10)}`,
                    borderRadius: 'var(--radius-sm)',
                    marginRight: '16px',
                    padding: '0 8px',
                    cursor: 'pointer',
                    boxSizing: 'border-box',
                    flexShrink: 0,
                  }}
                >
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      maxWidth: '180px',
                    }}
                    title={alert.title}
                  >
                    {alert.title}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <SeverityBadge score={alert.severity} showScore={false} />
                    <span
                      style={{
                        fontSize: '9px',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--text-muted)',
                      }}
                    >
                      {formatRelativeTime(alert.timestamp)}
                    </span>
                  </div>
                </div>
              ))}
              {/* Duplicate list for loop wrapping if enough alerts exist */}
              {alerts.length > 0 &&
                alerts.map((alert) => (
                  <div
                    key={`feed-2-${alert.id}`}
                    onClick={() => handleAlertClick(alert.country_id)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      width: '320px',
                      height: '28px',
                      backgroundColor: 'var(--bg-surface)',
                      borderLeft: `3px solid ${riskColor(alert.severity * 10)}`,
                      borderRadius: 'var(--radius-sm)',
                      marginRight: '16px',
                      padding: '0 8px',
                      cursor: 'pointer',
                      boxSizing: 'border-box',
                      flexShrink: 0,
                    }}
                  >
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        maxWidth: '180px',
                      }}
                    >
                      {alert.title}
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <SeverityBadge score={alert.severity} showScore={false} />
                      <span
                        style={{
                          fontSize: '9px',
                          fontFamily: 'var(--font-mono)',
                          color: 'var(--text-muted)',
                        }}
                      >
                        {formatRelativeTime(alert.timestamp)}
                      </span>
                    </div>
                  </div>
                ))}
              {alerts.length === 0 && (
                <div style={{ color: 'var(--text-muted)', fontSize: '12px', paddingLeft: '16px' }}>
                  No active high severity alerts. System operating normally.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Zone: Alert Drawer Button */}
        <div
          style={{
            width: '120px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            borderLeft: '1px solid var(--border)',
            height: '100%',
          }}
        >
          <button
            onClick={() => setDrawerOpen(true)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--accent-amber)',
              fontSize: '10px',
              fontWeight: 700,
              fontFamily: 'var(--font-display)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
              height: '100%',
              padding: '0 8px',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            <Bell size={12} />
            ▲ {alerts.length} ACTIVE
          </button>
        </div>
      </footer>

      {/* CSS keyframe for scrolling marquee */}
      <style>{`
        @keyframes marquee-scroll {
          0% { transform: translate3d(0, 0, 0); }
          100% { transform: translate3d(-50%, 0, 0); }
        }
      `}</style>

      {/* Alert Drawer Slide-over */}
      {drawerOpen && (
        <>
          <div
            onClick={() => setDrawerOpen(false)}
            style={{
              position: 'fixed',
              inset: 0,
              backgroundColor: 'rgba(0,0,0,0.6)',
              backdropFilter: 'blur(2px)',
              zIndex: 998,
            }}
          />
          <div
            style={{
              position: 'fixed',
              right: 0,
              bottom: 0,
              top: 0,
              width: '380px',
              maxWidth: '100%',
              backgroundColor: 'var(--bg-surface)',
              borderLeft: '1px solid var(--border)',
              boxShadow: 'var(--shadow)',
              zIndex: 999,
              display: 'flex',
              flexDirection: 'column',
              boxSizing: 'border-box',
              animation: 'slideIn 300ms var(--ease-snap)',
            }}
          >
            <div
              style={{
                padding: '16px',
                borderBottom: '1px solid var(--border)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertTriangle size={16} style={{ color: 'var(--accent-amber)' }} />
                <span
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontWeight: 700,
                    fontSize: '14px',
                    color: 'var(--text-primary)',
                  }}
                >
                  ACTIVE THREAT ALERTS ({alerts.length})
                </span>
              </div>
              <button
                onClick={() => setDrawerOpen(false)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  padding: '4px',
                }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Event Cards Stack */}
            <div
              style={{
                flex: 1,
                overflowY: 'auto',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              {alerts.length === 0 ? (
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '100%',
                    color: 'var(--text-muted)',
                    gap: '12px',
                  }}
                >
                  <Bell size={24} />
                  <span>No high-severity threats active.</span>
                </div>
              ) : (
                alerts.map((alert) => (
                  <div
                    key={alert.id}
                    onClick={() => handleAlertClick(alert.country_id)}
                    style={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border)',
                      borderLeft: `4px solid ${riskColor(alert.severity * 10)}`,
                      borderRadius: 'var(--radius-md)',
                      padding: '12px',
                      cursor: 'pointer',
                      transition: 'all 150ms var(--ease-snap)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = 'var(--bg-hover)';
                      e.currentTarget.style.borderColor = 'var(--border-bright)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = 'var(--bg-elevated)';
                      e.currentTarget.style.borderColor = 'var(--border)';
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
                      <h4
                        style={{
                          margin: 0,
                          fontSize: '13px',
                          fontWeight: 600,
                          color: 'var(--text-primary)',
                          lineHeight: 1.3,
                        }}
                      >
                        {alert.title}
                      </h4>
                      <SeverityBadge score={alert.severity} showScore={true} />
                    </div>
                    <p
                      style={{
                        margin: '8px 0',
                        fontSize: '11px',
                        color: 'var(--text-secondary)',
                        lineHeight: 1.4,
                      }}
                    >
                      {alert.description}
                    </p>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginTop: '8px',
                        fontSize: '10px',
                      }}
                    >
                      <span style={{ color: 'var(--text-muted)' }}>Source: {alert.source}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                        {formatRelativeTime(alert.timestamp)}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
          <style>{`
            @keyframes slideIn {
              from { transform: translateX(100%); }
              to { transform: translateX(0); }
            }
          `}</style>
        </>
      )}
    </>
  );
};

export default StatusBar;
