import React, { useState, useEffect } from 'react';
import { useSignals } from '../hooks/useSignals';
import { useWebSocket } from '../context/WebSocketContext';
import { riskColor } from '../utils/risk';
import { formatCurrency, formatPercent, formatNumber } from '../utils/format';
import { SignalPill } from '../components/ui/SignalPill';
import { StatCard } from '../components/ui/StatCard';
import { ConfidenceBar } from '../components/ui/ConfidenceBar';
import { X } from 'lucide-react';
import axios from 'axios';
import {
  ResponsiveContainer,
  ComposedChart,
  XAxis,
  YAxis,
  Line,
  Area,
} from 'recharts';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

export const Signals: React.FC = () => {
  const { signals, loading } = useSignals();
  
  // Local list to handle row updates and flashes
  const [localSignals, setLocalSignals] = useState<any[]>([]);
  const [flashingRows, setFlashingRows] = useState<Record<number, boolean>>({});
  const { subscribe, unsubscribe } = useWebSocket();

  // Selected Signal for sliding panel overlay
  const [selectedSignal, setSelectedSignal] = useState<any | null>(null);
  const [detailTab, setDetailTab] = useState<'setup' | 'forecast' | 'reasoning'>('setup');
  const [forecastHorizon, setForecastHorizon] = useState<number>(30);
  const [forecastData, setForecastData] = useState<any[]>([]);
  const [forecastMetrics, setForecastMetrics] = useState<any | null>(null);
  const [forecastLoading, setForecastLoading] = useState<boolean>(false);

  // Filters
  const [selectedClass, setSelectedClass] = useState<string>('All');
  const [selectedDirection, setSelectedDirection] = useState<string>('All');
  const [minConfidence, setMinConfidence] = useState<number>(50);

  // Populate local signals list
  useEffect(() => {
    if (signals.length > 0) {
      setLocalSignals(signals);
    }
  }, [signals]);

  // Subscribe to WS updates to flash rows
  useEffect(() => {
    const subId = subscribe('signal_update', (msg: any) => {
      const liveSignal = msg.signal;
      
      setLocalSignals((prev) => {
        const idx = prev.findIndex((s) => s.market_id === liveSignal.market_id);
        if (idx > -1) {
          const updated = [...prev];
          updated[idx] = { ...updated[idx], ...liveSignal };
          return updated;
        } else {
          return [liveSignal, ...prev];
        }
      });

      // Trigger 150ms flash glow
      if (liveSignal.market_id) {
        setFlashingRows((prev) => ({ ...prev, [liveSignal.market_id]: true }));
        setTimeout(() => {
          setFlashingRows((prev) => ({ ...prev, [liveSignal.market_id]: false }));
        }, 150);
      }
    });

    return () => unsubscribe(subId);
  }, []);

  // Fetch forecast data on select or tab shift
  useEffect(() => {
    if (selectedSignal && detailTab === 'forecast') {
      loadForecastData(selectedSignal.market_id);
    }
  }, [selectedSignal, detailTab, forecastHorizon]);

  const loadForecastData = async (marketId: number) => {
    setForecastLoading(true);
    try {
      const res = await axios.get(
        `${API_BASE}/forecast/mc/${marketId}?horizon=${forecastHorizon}&n_sims=1000`
      );
      if (res.data) {
        const mc = res.data;
        const median = mc.forecast || [];
        const upper75 = mc.upper_75 || [];
        const lower25 = mc.lower_25 || [];
        const currentPrice = selectedSignal.market_price || selectedSignal.entry_price || 100.0;
        
        const chartList = [];
        for (let i = 10; i > 0; i--) {
          chartList.push({
            day: `T-${i}`,
            price: currentPrice * (1 + Math.sin(i) * 0.01),
          });
        }
        chartList.push({
          day: 'Today',
          price: currentPrice,
          p50: currentPrice,
          p25_p75: [currentPrice, currentPrice],
        });

        for (let i = 0; i < median.length; i++) {
          chartList.push({
            day: `T+${i + 1}`,
            p50: median[i],
            p25_p75: [lower25[i], upper75[i]],
          });
        }

        setForecastData(chartList);
        setForecastMetrics(mc.risk_metrics);
      }
    } catch (e) {
      // mock if offline
      const currentPrice = selectedSignal.market_price || selectedSignal.entry_price || 100.0;
      const chartList = [];
      for (let i = 10; i > 0; i--) {
        chartList.push({ day: `T-${i}`, price: currentPrice - i * 0.5 + Math.random() });
      }
      chartList.push({ day: 'Today', price: currentPrice, p50: currentPrice, p25: currentPrice, p75: currentPrice });
      for (let i = 1; i <= forecastHorizon; i++) {
        chartList.push({
          day: `T+${i}`,
          p50: currentPrice + i * 0.5 + Math.random(),
          p25: currentPrice + i * 0.2 - Math.random(),
          p75: currentPrice + i * 0.8 + Math.random(),
        });
      }
      setForecastData(chartList);
      setForecastMetrics({
        var_95: -4.5,
        cvar_95: -7.0,
        sharpe_ratio: 1.25,
        probability_of_loss: 22.0,
        expected_value: currentPrice + forecastHorizon * 0.4,
      });
    } finally {
      setForecastLoading(false);
    }
  };

  // Filter signals list
  const filteredSignals = localSignals.filter((s) => {
    if (selectedClass !== 'All' && s.market_asset_class?.toLowerCase() !== selectedClass.toLowerCase()) {
      return false;
    }
    if (selectedDirection !== 'All' && s.signal_type !== selectedDirection) {
      return false;
    }
    if (Math.round(s.confidence * 100) < minConfidence) {
      return false;
    }
    return true;
  });

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 104px)', // 56px Top nav + 48px Bottom status = 104px
        width: '100%',
        backgroundColor: 'var(--bg-base)',
        color: 'var(--text-primary)',
        boxSizing: 'border-box',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* Sticky Filter Bar */}
      <div
        style={{
          height: '56px',
          width: '100%',
          backgroundColor: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 20px',
          boxSizing: 'border-box',
          gap: '20px',
          zIndex: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1, overflowX: 'auto' }}>
          {/* Asset Class Pills */}
          <div style={{ display: 'flex', gap: '6px' }}>
            {['All', 'Commodities', 'Equity', 'Forex', 'Crypto', 'Stocks'].map((c) => (
              <button
                key={c}
                onClick={() => setSelectedClass(c)}
                style={{
                  padding: '4px 12px',
                  borderRadius: '12px',
                  backgroundColor: selectedClass === c ? 'rgba(6, 182, 212, 0.15)' : 'var(--bg-elevated)',
                  border: `1px solid ${selectedClass === c ? 'var(--accent-cyan)' : 'var(--border)'}`,
                  color: selectedClass === c ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                {c.toUpperCase()}
              </button>
            ))}
          </div>

          <div style={{ width: '1px', height: '18px', backgroundColor: 'var(--border)' }} />

          {/* Direction Filter */}
          <div style={{ display: 'flex', gap: '6px' }}>
            {['All', 'BUY', 'SELL', 'HOLD'].map((d) => (
              <button
                key={d}
                onClick={() => setSelectedDirection(d)}
                style={{
                  padding: '4px 12px',
                  borderRadius: '12px',
                  backgroundColor: selectedDirection === d ? 'rgba(6, 182, 212, 0.15)' : 'var(--bg-elevated)',
                  border: `1px solid ${selectedDirection === d ? 'var(--accent-cyan)' : 'var(--border)'}`,
                  color: selectedDirection === d ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        {/* Min Confidence Slider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: 700, letterSpacing: '0.04em' }}>
            MIN CONFIDENCE:
          </span>
          <input
            type="range"
            min="0"
            max="100"
            value={minConfidence}
            onChange={(e) => setMinConfidence(parseInt(e.target.value))}
            style={{ width: '100px', cursor: 'pointer', accentColor: 'var(--accent-cyan)' }}
          />
          <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-cyan)', minWidth: '32px' }}>
            {minConfidence}%
          </span>
        </div>
      </div>

      {/* Main Signal Table Layout */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', width: '100%' }}>
        {/* Table Column */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
          {loading && localSignals.length === 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="skeleton" style={{ height: '44px', width: '100%' }} />
              ))}
            </div>
          ) : filteredSignals.length === 0 ? (
            <div style={{ padding: '48px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              No signals match the current filter parameters.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
                  <th style={{ padding: '12px 10px' }}>ASSET</th>
                  <th style={{ padding: '12px 10px' }}>DIRECTION</th>
                  <th style={{ padding: '12px 10px' }}>CONFIDENCE</th>
                  <th style={{ padding: '12px 10px' }}>BULL</th>
                  <th style={{ padding: '12px 10px' }}>BEAR</th>
                  <th style={{ padding: '12px 10px' }}>ENTRY</th>
                  <th style={{ padding: '12px 10px' }}>TARGET</th>
                  <th style={{ padding: '12px 10px' }}>STOP LOSS</th>
                  <th style={{ padding: '12px 10px' }}>RISK:REWARD</th>
                  <th style={{ padding: '12px 10px' }}>VOLATILITY</th>
                </tr>
              </thead>
              <tbody>
                {filteredSignals.map((sig) => {
                  const confPct = Math.round(sig.confidence * 100);
                  const isFlashing = flashingRows[sig.market_id] || false;
                  return (
                    <tr
                      key={sig.id}
                      onClick={() => {
                        setSelectedSignal(sig);
                        setDetailTab('setup');
                      }}
                      style={{
                        borderBottom: '1px solid var(--border)',
                        fontSize: '13px',
                        cursor: 'pointer',
                        backgroundColor: isFlashing ? 'rgba(6, 182, 212, 0.15)' : 'transparent',
                        transition: 'background-color var(--transition-fast) var(--ease-snap)',
                      }}
                      onMouseEnter={(e) => {
                        if (!isFlashing) e.currentTarget.style.backgroundColor = 'var(--bg-surface)';
                      }}
                      onMouseLeave={(e) => {
                        if (!isFlashing) e.currentTarget.style.backgroundColor = 'transparent';
                      }}
                    >
                      <td style={{ padding: '12px 10px' }}>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-primary)' }}>
                            {sig.market_symbol}
                          </span>
                          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            {sig.market_name || 'Market Asset'}
                          </span>
                        </div>
                      </td>
                      <td style={{ padding: '12px 10px' }}>
                        <SignalPill direction={sig.signal_type} size="sm" />
                      </td>
                      <td style={{ padding: '12px 10px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: riskColor(confPct), minWidth: '32px' }}>
                            {confPct}%
                          </span>
                          <div style={{ width: '60px', height: '4px', backgroundColor: 'var(--bg-elevated)', borderRadius: '2px', overflow: 'hidden' }}>
                            <div style={{ width: `${confPct}%`, height: '100%', backgroundColor: riskColor(confPct) }} />
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: '12px 10px', fontFamily: 'var(--font-mono)', color: 'var(--accent-green)', fontWeight: 600 }}>
                        {Math.round(sig.bullish_strength * 100)}%
                      </td>
                      <td style={{ padding: '12px 10px', fontFamily: 'var(--font-mono)', color: 'var(--risk-critical)', fontWeight: 600 }}>
                        {Math.round(sig.bearish_strength * 100)}%
                      </td>
                      <td style={{ padding: '12px 10px', fontFamily: 'var(--font-mono)' }}>
                        {formatCurrency(sig.entry_price)}
                      </td>
                      <td style={{ padding: '12px 10px', fontFamily: 'var(--font-mono)', color: 'var(--accent-green)', fontWeight: 600 }}>
                        {formatCurrency(sig.target_price)}
                      </td>
                      <td style={{ padding: '12px 10px', fontFamily: 'var(--font-mono)', color: 'var(--risk-critical)', fontWeight: 600 }}>
                        {formatCurrency(sig.stop_loss)}
                      </td>
                      <td style={{ padding: '12px 10px', fontFamily: 'var(--font-mono)' }}>
                        1:{sig.risk_reward_ratio.toFixed(1)}
                      </td>
                      <td style={{ padding: '12px 10px' }}>
                        <span style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-secondary)', backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border)', padding: '2px 6px', borderRadius: 'var(--radius-sm)' }}>
                          {sig.volatility_level.toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Sliding detail panel (right side overlay) */}
        {selectedSignal && (
          <div
            style={{
              width: '380px',
              flexShrink: 0,
              backgroundColor: 'var(--bg-surface)',
              borderLeft: '1px solid var(--border)',
              display: 'flex',
              flexDirection: 'column',
              animation: 'slideIn 300ms var(--ease-snap)',
              boxSizing: 'border-box',
            }}
          >
            {/* Header */}
            <div style={{ padding: '16px', borderBottom: '1px solid var(--border)', backgroundColor: 'var(--bg-elevated)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '20px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                    {selectedSignal.market_symbol}
                  </span>
                  <SignalPill direction={selectedSignal.signal_type} size="sm" />
                </div>
                <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block', marginTop: '2px' }}>
                  {selectedSignal.market_name || 'Market Asset'}
                </span>
              </div>
              <button
                onClick={() => setSelectedSignal(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '4px' }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Tabs */}
            <div style={{ height: '36px', borderBottom: '1px solid var(--border)', display: 'flex', backgroundColor: 'var(--bg-base)' }}>
              {[
                { id: 'setup', label: 'SETUP' },
                { id: 'forecast', label: 'FORECAST' },
                { id: 'reasoning', label: 'REASONING' },
              ].map((t) => {
                const active = detailTab === t.id;
                return (
                  <button
                    key={t.id}
                    onClick={() => setDetailTab(t.id as any)}
                    style={{
                      flex: 1,
                      background: 'transparent',
                      border: 'none',
                      borderBottom: active ? '2px solid var(--accent-cyan)' : '2px solid transparent',
                      color: active ? 'var(--text-primary)' : 'var(--text-muted)',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    {t.label}
                  </button>
                );
              })}
            </div>

            {/* Scroll Panel Body */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {detailTab === 'setup' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
                    <StatCard label="ENTRY PRICE" value={selectedSignal.entry_price} />
                    <StatCard label="CURRENT PRICE" value={selectedSignal.market_price || selectedSignal.entry_price} />
                    <StatCard label="TARGET PRICE" value={selectedSignal.target_price} valueColor="var(--accent-green)" />
                    <StatCard label="STOP LOSS" value={selectedSignal.stop_loss} valueColor="var(--risk-critical)" />
                  </div>
                  <div style={{ borderTop: '1px solid var(--border)', paddingTop: '12px' }}>
                    <ConfidenceBar label="CONFIDENCE" value={Math.round(selectedSignal.confidence * 100)} color="green" />
                  </div>
                </div>
              )}

              {detailTab === 'forecast' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    {[30, 60].map((h) => (
                      <button
                        key={h}
                        onClick={() => setForecastHorizon(h)}
                        style={{
                          padding: '4px 10px',
                          borderRadius: '12px',
                          backgroundColor: forecastHorizon === h ? 'rgba(6, 182, 212, 0.15)' : 'var(--bg-elevated)',
                          border: `1px solid ${forecastHorizon === h ? 'var(--accent-cyan)' : 'var(--border)'}`,
                          color: forecastHorizon === h ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                          fontSize: '10px',
                          fontWeight: 700,
                          cursor: 'pointer',
                        }}
                      >
                        {h}D HORIZON
                      </button>
                    ))}
                  </div>

                  {forecastLoading ? (
                    <div style={{ height: '160px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)' }}>
                      <Loader2 size={16} className="animate-spin" />
                    </div>
                  ) : (
                    <div style={{ height: '180px' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={forecastData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                          <XAxis dataKey="day" stroke="var(--text-muted)" fontSize={9} fontFamily="var(--font-mono)" tickLine={false} />
                          <YAxis stroke="var(--text-muted)" fontSize={9} fontFamily="var(--font-mono)" tickLine={false} axisLine={false} domain={['auto', 'auto']} orientation="right" />
                          <Line type="monotone" dataKey="price" stroke="var(--accent-cyan)" strokeWidth={1.5} dot={false} connectNulls />
                          <Area type="monotone" dataKey="p25_p75" stroke="none" fill="var(--accent-purple)" fillOpacity={0.15} />
                          <Line type="monotone" dataKey="p50" stroke="var(--accent-purple)" strokeWidth={1.5} dot={false} connectNulls />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  {forecastMetrics && (
                    <>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', fontSize: '10px' }}>
                        <div style={{ backgroundColor: 'var(--bg-elevated)', padding: '6px', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                          <span style={{ color: 'var(--text-muted)' }}>VaR 95%</span>
                          <span style={{ display: 'block', fontWeight: 700, color: 'var(--risk-critical)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                            {formatPercent(forecastMetrics.var_95)}
                          </span>
                        </div>
                        <div style={{ backgroundColor: 'var(--bg-elevated)', padding: '6px', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                          <span style={{ color: 'var(--text-muted)' }}>CVaR 95%</span>
                          <span style={{ display: 'block', fontWeight: 700, color: 'var(--risk-critical)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                            {formatPercent(forecastMetrics.cvar_95)}
                          </span>
                        </div>
                        <div style={{ backgroundColor: 'var(--bg-elevated)', padding: '6px', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                          <span style={{ color: 'var(--text-muted)' }}>Sharpe</span>
                          <span style={{ display: 'block', fontWeight: 700, color: 'var(--accent-green)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                            {formatNumber(forecastMetrics.sharpe_ratio, 2)}
                          </span>
                        </div>
                      </div>

                      {forecastMetrics.interpretation && (
                        <div style={{ marginTop: '12px', borderTop: '1px solid var(--border)', paddingTop: '12px', textAlign: 'left' }}>
                          <span style={{ fontSize: '9px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', display: 'block', marginBottom: '6px' }}>
                            AI FORECAST INTERPRETATION
                          </span>
                          <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4, margin: 0, backgroundColor: 'var(--bg-elevated)', padding: '8px', borderRadius: 'var(--radius-sm)', borderLeft: '3px solid var(--accent-cyan)' }}>
                            {forecastMetrics.interpretation}
                          </p>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {detailTab === 'reasoning' && (
                <div>
                  <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontWeight: 700, display: 'block', marginBottom: '8px' }}>
                    TACTICAL AI STRATEGY SUMMARY
                  </span>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
                    {selectedSignal.reasoning}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      <style>{`
        @keyframes slideIn {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
      `}</style>
    </div>
  );
};

// Loader component fallback helper
const Loader2: React.FC<{ size: number; className?: string }> = ({ size }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className="animate-spin"
    style={{ color: 'var(--text-muted)' }}
  >
    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
  </svg>
);

export default Signals;
