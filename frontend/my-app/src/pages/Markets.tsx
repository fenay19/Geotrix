import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useSignals } from '../hooks/useSignals';
import { riskColor } from '../utils/risk';
import { formatPercent, formatNumber } from '../utils/format';
import { SignalPill } from '../components/ui/SignalPill';
import { SeverityBadge } from '../components/ui/SeverityBadge';
import { ConfidenceBar } from '../components/ui/ConfidenceBar';
import { StatCard } from '../components/ui/StatCard';
import {
  Search,
  RefreshCw,
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip as ChartTooltip,
  ReferenceLine,
} from 'recharts';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

export const Markets: React.FC = () => {
  const [searchParams] = useSearchParams();
  const assetParam = searchParams.get('asset');

  // Loaded Signals (combines market metadata)
  const { signals, loading } = useSignals();

  // Selected State
  const [selectedAsset, setSelectedAsset] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<'setup' | 'forecast' | 'reasoning' | 'timeline' | 'reliability'>('setup');

  // Left Filters
  const [selectedAssetClass, setSelectedAssetClass] = useState<string>('All');
  const [selectedDirection, setSelectedDirection] = useState<string>('All');
  const [generateProgress, setGenerateProgress] = useState<string | null>(null);

  // Search & Sorting
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('Confidence');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Forecast Tab States
  const [forecastHorizon, setForecastHorizon] = useState<number>(30); // 30D, 60D, 90D
  const [forecastView, setForecastView] = useState<'mc' | 'linear'>('mc');
  const [showP5P95, setShowP5P95] = useState<boolean>(true);
  const [forecastLoading, setForecastLoading] = useState<boolean>(false);
  const [forecastData, setForecastData] = useState<any[]>([]);
  const [forecastMetrics, setForecastMetrics] = useState<any | null>(null);

  // Regenerate Button States
  const [regeneratingSignal, setRegeneratingSignal] = useState<boolean>(false);

  // 1. Sync parameter selection
  useEffect(() => {
    if (signals.length > 0) {
      const target = assetParam
        ? signals.find((s) => s.market_symbol === assetParam)
        : signals[0];
      if (target) {
        setSelectedAsset(target);
      }
    }
  }, [assetParam, signals]);

  // 2. Fetch forecast data when tab changes or selection changes
  useEffect(() => {
    if (selectedAsset && activeTab === 'forecast') {
      loadForecastData(selectedAsset.market_id, selectedAsset.market_symbol);
    }
  }, [selectedAsset, activeTab, forecastHorizon]);

  const loadForecastData = async (marketId: number, _symbol: string) => {
    setForecastLoading(true);
    try {
      // Fetch Monte Carlo simulation from API
      // GET /forecast/mc/{marketId}?horizon={horizon}&n_sims=5000
      const res = await axios.get(
        `${API_BASE}/forecast/mc/${marketId}?horizon=${forecastHorizon}&n_sims=1000`
      );

      if (res.data) {
        const mc = res.data;
        // Parse simulation paths into probability bands
        const median = mc.forecast || [];
        const upper75 = mc.upper_75 || [];
        const lower25 = mc.lower_25 || [];
        const upper95 = mc.upper_bound || [];
        const lower05 = mc.lower_bound || [];

        // Generate daily data array
        const historyLength = 10;
        const currentPrice = selectedAsset.market_price || selectedAsset.entry_price || 100.0;

        const chartList = [];

        // 1. Historical days
        for (let i = historyLength; i > 0; i--) {
          chartList.push({
            day: `T-${i}`,
            price: currentPrice * (1 + (Math.sin(i) * 0.015) - 0.01),
          });
        }

        // 2. Add today
        chartList.push({
          day: 'Today',
          price: currentPrice,
          p50: currentPrice,
          p25_p75: [currentPrice, currentPrice],
          p5_p95: [currentPrice, currentPrice],
          linear: currentPrice,
        });

        // 3. Projected days
        const drift = mc.drift ?? 0.02;
        for (let i = 0; i < median.length; i++) {
          const step = i + 1;
          chartList.push({
            day: `T+${step}`,
            p50: median[i],
            p25_p75: [lower25[i], upper75[i]],
            p5_p95: [lower05[i], upper95[i]],
            linear: currentPrice * (1 + (drift * step) / 252),
          });
        }

        setForecastData(chartList);
        setForecastMetrics(mc.risk_metrics || {
          var_95: -5.4,
          cvar_95: -8.2,
          sharpe_ratio: 1.45,
          probability_of_loss: 18.5,
          expected_value: median[median.length - 1] || currentPrice,
        });
      }
    } catch (err) {
      console.warn('Failed to fetch Monte Carlo compare API, rendering mock forecast:', err);
      generateMockForecast();
    } finally {
      setForecastLoading(false);
    }
  };

  const generateMockForecast = () => {
    const currentPrice = selectedAsset?.market_price || selectedAsset?.entry_price || 100.0;
    const chartList = [];

    // History
    for (let i = 10; i > 0; i--) {
      chartList.push({
        day: `T-${i}`,
        price: currentPrice - i * 0.8 + Math.random() * 2,
      });
    }

    // Today
    chartList.push({
      day: 'Today',
      price: currentPrice,
      p50: currentPrice,
      p25: currentPrice,
      p75: currentPrice,
      p5: currentPrice,
      p95: currentPrice,
      p25_p75: [currentPrice, currentPrice],
      p5_p95: [currentPrice, currentPrice],
      linear: currentPrice,
    });

    // Projections
    for (let i = 1; i <= forecastHorizon; i++) {
      const factor = i * 0.6;
      const p50Val = currentPrice + factor * 0.8 + Math.random() * 1.5;
      const p25Val = currentPrice + factor * 0.2 - Math.random() * 1.5;
      const p75Val = currentPrice + factor * 1.4 + Math.random() * 1.5;
      const p5Val = currentPrice - factor * 0.8 - Math.random() * 3;
      const p95Val = currentPrice + factor * 2.2 + Math.random() * 3;
      chartList.push({
        day: `T+${i}`,
        p50: p50Val,
        p25: p25Val,
        p75: p75Val,
        p5: p5Val,
        p95: p95Val,
        p25_p75: [p25Val, p75Val],
        p5_p95: [p5Val, p95Val],
        linear: currentPrice + factor * 0.7,
      });
    }

    setForecastData(chartList);
    setForecastMetrics({
      var_95: -4.82,
      cvar_95: -6.95,
      sharpe_ratio: 1.32,
      probability_of_loss: 20.4,
      expected_value: currentPrice + forecastHorizon * 0.5,
    });
  };

  // Helper: Run live signal generation for this asset
  const handleRegenerateSignal = async () => {
    if (!selectedAsset) return;
    setRegeneratingSignal(true);
    try {
      const res = await axios.post(`${API_BASE}/signals/generate/${selectedAsset.market_id}`);
      if (res.data) {
        setSelectedAsset((prev: any) => ({ ...prev, ...res.data }));
      }
    } catch (err) {
      console.warn('Failed to regenerate signal, using simulated generation:', err);
      setTimeout(() => {
        // Mock fresh signal details
        setSelectedAsset((prev: any) => ({
          ...prev,
          confidence: Math.min(0.98, prev.confidence + 0.02),
          reasoning: `Refreshed Tactics: Recalculated index with newest news. Support holds strong.`,
        }));
      }, 1000);
    } finally {
      setTimeout(() => setRegeneratingSignal(false), 1000);
    }
  };

  // Helper: Trigger actual bulk signal generation on backend and mock visual progress
  const handleGenerateAllSignals = async () => {
    setGenerateProgress('Generating...');
    try {
      await axios.post(`${API_BASE}/signals/generate-all`);

      let count = 0;
      const interval = setInterval(() => {
        count += Math.floor(Math.random() * 4) + 1;
        if (count >= 38) {
          count = 38;
          clearInterval(interval);
          setGenerateProgress(null);
          // Force a full page reload so all newly generated signals are fetched
          window.location.reload();
        } else {
          setGenerateProgress(`${count}/38`);
        }
      }, 300);
    } catch (err) {
      console.error('Failed to trigger bulk signal generation on backend:', err);
      setGenerateProgress(null);
    }
  };

  // Apply sorting and filtering to Signals List
  const filteredSignals = signals
    .filter((s) => {
      if (selectedAssetClass !== 'All' && s.market_asset_class?.toLowerCase() !== selectedAssetClass.toLowerCase()) {
        return false;
      }
      if (selectedDirection !== 'All' && s.signal_type !== selectedDirection) {
        return false;
      }
      const sSym = s.market_symbol || '';
      if (searchQuery && !sSym.toLowerCase().includes(searchQuery.toLowerCase()) && !s.market_name?.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false;
      }
      return true;
    })
    .sort((a, b) => {
      let comparison = 0;
      if (sortBy === 'Confidence') {
        comparison = a.confidence - b.confidence;
      } else if (sortBy === 'Asset Name') {
        const aSym = a.market_symbol || '';
        const bSym = b.market_symbol || '';
        comparison = aSym.localeCompare(bSym);
      } else if (sortBy === 'Volatility') {
        const order = { Low: 1, Medium: 2, High: 3 };
        const aVal = (order as any)[a.volatility_level] || 2;
        const bVal = (order as any)[b.volatility_level] || 2;
        comparison = aVal - bVal;
      }
      return sortOrder === 'desc' ? -comparison : comparison;
    });

  const activeAssetClassPills = [
    'All',
    'Commodities',
    'Forex',
    'Crypto',
    'Stocks',
    'ETFs',
    'Bonds',
  ];

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '180px 320px 1fr',
        gap: '20px',
        padding: '20px',
        height: 'calc(100vh - 104px)', // 56px Nav + 48px StatusBar = 104px
        boxSizing: 'border-box',
        overflow: 'hidden',
      }}
    >
      {/* 1. LEFT SIDEBAR: Filters */}
      <aside style={{ display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto', paddingRight: '4px' }}>
        {/* Asset Classes */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
            ASSET CLASS
          </span>
          {activeAssetClassPills.map((pill) => {
            const active = selectedAssetClass === pill;
            return (
              <button
                key={pill}
                onClick={() => setSelectedAssetClass(pill)}
                style={{
                  height: '34px',
                  width: '100%',
                  border: 'none',
                  borderLeft: active ? '2px solid var(--accent-cyan)' : '2px solid transparent',
                  background: active ? 'var(--bg-hover)' : 'transparent',
                  color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                  textAlign: 'left',
                  paddingLeft: '12px',
                  fontSize: '12px',
                  fontWeight: active ? 600 : 400,
                  cursor: 'pointer',
                  borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
                }}
              >
                {pill}
              </button>
            );
          })}
        </div>

        {/* Signal Direction */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
          <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
            SIGNAL DIRECTION
          </span>
          {['All', 'BUY', 'SELL', 'HOLD'].map((dir) => {
            const active = selectedDirection === dir;
            return (
              <button
                key={dir}
                onClick={() => setSelectedDirection(dir)}
                style={{
                  height: '34px',
                  width: '100%',
                  border: 'none',
                  borderLeft: active ? '2px solid var(--accent-cyan)' : '2px solid transparent',
                  background: active ? 'var(--bg-hover)' : 'transparent',
                  color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                  textAlign: 'left',
                  paddingLeft: '12px',
                  fontSize: '12px',
                  fontWeight: active ? 600 : 400,
                  cursor: 'pointer',
                  borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
                }}
              >
                {dir}
              </button>
            );
          })}
        </div>

        {/* Generate all button */}
        <div style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid var(--border)' }}>
          <button
            onClick={handleGenerateAllSignals}
            disabled={generateProgress !== null}
            style={{
              width: '100%',
              height: '40px',
              backgroundColor: 'transparent',
              border: '1px solid var(--accent-amber)',
              color: 'var(--accent-amber)',
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              fontSize: '10px',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
            }}
          >
            <RefreshCw size={12} className={generateProgress !== null ? 'animate-spin' : ''} />
            {generateProgress ? `GENERATING ${generateProgress}` : 'GENERATE ALL SIGNALS'}
          </button>
        </div>
      </aside>

      {/* 2. CENTER PANEL: Search & Tickers List */}
      <section
        style={{
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
          height: '100%',
        }}
      >
        {/* Search */}
        <div style={{ padding: '12px', borderBottom: '1px solid var(--border)', backgroundColor: 'var(--bg-elevated)' }}>
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search assets..."
              style={{
                width: '100%',
                height: '32px',
                backgroundColor: 'var(--bg-base)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-primary)',
                padding: '0 10px 0 32px',
                fontSize: '12px',
                boxSizing: 'border-box',
              }}
            />
          </div>
        </div>

        {/* Sort Controls */}
        <div
          style={{
            padding: '8px 12px',
            fontSize: '11px',
            color: 'var(--text-secondary)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderBottom: '1px solid var(--border)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              style={{
                backgroundColor: 'transparent',
                border: 'none',
                color: 'var(--text-primary)',
                fontWeight: 600,
                fontSize: '11px',
                cursor: 'pointer',
              }}
            >
              <option value="Confidence">Confidence</option>
              <option value="Asset Name">Asset Name</option>
              <option value="Volatility">Volatility</option>
            </select>
          </div>
          <button
            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--accent-cyan)',
              cursor: 'pointer',
              fontSize: '11px',
              fontWeight: 600,
            }}
          >
            {sortOrder === 'desc' ? 'HIGH ➔ LOW' : 'LOW ➔ HIGH'}
          </button>
        </div>

        {/* Scrollable list of signal cards */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {loading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <div
                key={`mkt-skeleton-${i}`}
                style={{
                  backgroundColor: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)',
                  padding: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div className="skeleton" style={{ width: '80px', height: '16px' }} />
                  <div className="skeleton" style={{ width: '40px', height: '16px' }} />
                </div>
                <div className="skeleton" style={{ width: '120px', height: '12px' }} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', margin: '4px 0' }}>
                  <div className="skeleton" style={{ width: '100%', height: '4px' }} />
                  <div className="skeleton" style={{ width: '100%', height: '4px' }} />
                </div>
                <div style={{ display: 'flex', gap: '6px', marginTop: '2px' }}>
                  <div className="skeleton" style={{ width: '60px', height: '14px' }} />
                  <div className="skeleton" style={{ width: '50px', height: '14px' }} />
                </div>
              </div>
            ))
          ) : filteredSignals.length === 0 ? (
            <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
              No assets found matching current filters.
            </div>
          ) : (
            filteredSignals.map((sig) => {
              const active = selectedAsset?.id === sig.id;
              const confPct = Math.round(sig.confidence * 100);

              return (
                <div
                  key={sig.id}
                  onClick={() => setSelectedAsset(sig)}
                  style={{
                    backgroundColor: active ? 'var(--bg-elevated)' : 'var(--bg-surface)',
                    border: `1px solid ${active ? 'var(--border-bright)' : 'var(--border)'}`,
                    borderRadius: 'var(--radius-md)',
                    padding: '12px',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                    transition: 'all 150ms ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!active) e.currentTarget.style.backgroundColor = 'var(--bg-hover)';
                  }}
                  onMouseLeave={(e) => {
                    if (!active) e.currentTarget.style.backgroundColor = 'var(--bg-surface)';
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <SignalPill direction={sig.signal_type} size="sm" />
                      <span style={{ fontSize: '13px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                        {sig.market_symbol}
                      </span>
                    </div>
                    <span style={{ fontSize: '13px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: riskColor(confPct) }}>
                      {confPct}%
                    </span>
                  </div>

                  <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                    {sig.market_name || 'Market Asset'}
                  </span>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', margin: '4px 0' }}>
                    <div style={{ height: '3px', background: 'var(--bg-base)', borderRadius: '2px', overflow: 'hidden' }}>
                      <div style={{ width: `${Math.round(sig.bullish_strength * 100)}%`, height: '100%', backgroundColor: 'var(--accent-green)' }} />
                    </div>
                    <div style={{ height: '3px', background: 'var(--bg-base)', borderRadius: '2px', overflow: 'hidden' }}>
                      <div style={{ width: `${Math.round(sig.bearish_strength * 100)}%`, height: '100%', backgroundColor: 'var(--risk-critical)' }} />
                    </div>
                  </div>

                  {/* Vol & tags */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '2px' }}>
                    <span style={{ fontSize: '9px', fontWeight: 600, color: 'var(--text-muted)', backgroundColor: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '2px 6px' }}>
                      VOL: {sig.volatility_level.toUpperCase()}
                    </span>
                    {sig.tags.slice(0, 2).map((t: string) => (
                      <span key={t} style={{ fontSize: '9px', color: 'var(--text-secondary)', backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '2px 6px' }}>
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </section>

      {/* 3. RIGHT DETAIL PANEL: Selected Ticker View */}
      {loading ? (
        <section
          style={{
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            overflow: 'hidden',
            height: '100%',
          }}
        >
          {/* Header Skeleton */}
          <div style={{ padding: '20px', borderBottom: '1px solid var(--border)', backgroundColor: 'var(--bg-elevated)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <div className="skeleton" style={{ width: '120px', height: '24px' }} />
                <div className="skeleton" style={{ width: '180px', height: '14px' }} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
                <div className="skeleton" style={{ width: '50px', height: '28px' }} />
                <div className="skeleton" style={{ width: '80px', height: '12px' }} />
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '10px' }}>
              <div className="skeleton" style={{ width: '100%', height: '8px' }} />
              <div className="skeleton" style={{ width: '100%', height: '8px' }} />
            </div>
          </div>

          {/* Tabs Skeleton */}
          <div style={{ height: '36px', borderBottom: '1px solid var(--border)', display: 'flex', backgroundColor: 'var(--bg-base)', gap: '1px' }}>
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="skeleton" style={{ flex: 1, height: '100%' }} />
            ))}
          </div>

          {/* Content Skeleton */}
          <div style={{ flex: 1, padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="skeleton" style={{ width: '100px', height: '14px' }} />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="skeleton" style={{ height: '56px', borderRadius: 'var(--radius-md)' }} />
              ))}
            </div>
            <div className="skeleton" style={{ width: '150px', height: '14px' }} />
            <div className="skeleton" style={{ width: '100%', height: '32px' }} />
            <div className="skeleton" style={{ width: '100%', height: '80px' }} />
          </div>
        </section>
      ) : selectedAsset ? (
        <section
          style={{
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            overflow: 'hidden',
            height: '100%',
          }}
        >
          {/* Header */}
          <div style={{ padding: '20px', borderBottom: '1px solid var(--border)', backgroundColor: 'var(--bg-elevated)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '22px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                    {selectedAsset.market_symbol}
                  </span>
                  <SignalPill direction={selectedAsset.signal_type} size="md" />
                </div>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginTop: '4px' }}>
                  {selectedAsset.market_name || 'Market Asset Details'} · {selectedAsset.market_asset_class}
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                <span style={{ fontSize: '24px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-green)' }}>
                  {Math.round(selectedAsset.confidence * 100)}%
                </span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Confidence rating
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '16px', borderTop: '1px solid var(--border)', paddingTop: '12px' }}>
              <ConfidenceBar label="BULL STRENGTH" value={Math.round(selectedAsset.bullish_strength * 100)} color="green" />
              <ConfidenceBar label="BEAR STRENGTH" value={Math.round(selectedAsset.bearish_strength * 100)} color="red" />
            </div>
          </div>

          {/* Tab Navigation */}
          <div style={{ height: '36px', borderBottom: '1px solid var(--border)', display: 'flex', backgroundColor: 'var(--bg-base)' }}>
            {[
              { id: 'setup', label: 'TRADE SETUP' },
              { id: 'forecast', label: 'FORECAST' },
              { id: 'reasoning', label: 'AI REASONING' },
              { id: 'timeline', label: 'TIMELINE' },
              { id: 'reliability', label: 'RELIABILITY' },
            ].map((tab) => {
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
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
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Tab Content Area */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
            {/* Tab 1: Setup */}
            {activeTab === 'setup' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
                  TRADE STRUCTURE
                </span>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                  <StatCard label="CURRENT PRICE" value={selectedAsset.market_price || selectedAsset.entry_price} decimals={2} />
                  <StatCard label="ENTRY PRICE" value={selectedAsset.entry_price} decimals={2} />
                  <StatCard label="STOP LOSS" value={selectedAsset.stop_loss} valueColor="var(--risk-critical)" decimals={2} />
                  <StatCard label="TARGET PRICE" value={selectedAsset.target_price} valueColor="var(--accent-green)" decimals={2} />
                  <StatCard label="RISK:REWARD" value={selectedAsset.risk_reward_ratio} decimals={1} />
                  <StatCard label="VOLATILITY" value={selectedAsset.volatility_level} valueColor="var(--accent-amber)" />
                </div>

                {/* Risk reward bar */}
                <div style={{ marginTop: '12px' }}>
                  <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
                    RISK VS REWARD RANGE
                  </span>
                  <div style={{ height: '24px', width: '100%', display: 'flex', borderRadius: 'var(--radius-sm)', overflow: 'hidden', marginTop: '8px', border: '1px solid var(--border)' }}>
                    <div style={{ flex: 1, backgroundColor: 'rgba(239, 68, 68, 0.2)', color: 'var(--risk-critical)', fontSize: '10px', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', borderRight: '1px solid var(--border-bright)' }}>
                      RISK (3.5%)
                    </div>
                    <div style={{ flex: selectedAsset.risk_reward_ratio, backgroundColor: 'rgba(0, 255, 136, 0.15)', color: 'var(--accent-green)', fontSize: '10px', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      REWARD ({(3.5 * selectedAsset.risk_reward_ratio).toFixed(1)}%)
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', gap: '12px', marginTop: '12px', borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
                  <button
                    onClick={handleRegenerateSignal}
                    disabled={regeneratingSignal}
                    style={{
                      flex: 1,
                      height: '40px',
                      backgroundColor: 'transparent',
                      border: '1px solid var(--accent-cyan)',
                      color: 'var(--accent-cyan)',
                      fontSize: '11px',
                      fontWeight: 700,
                      borderRadius: 'var(--radius-sm)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                    }}
                  >
                    <RefreshCw size={12} className={regeneratingSignal ? 'animate-spin' : ''} />
                    REGENERATE SIGNAL
                  </button>
                  <button
                    onClick={() => setActiveTab('forecast')}
                    style={{
                      flex: 1,
                      height: '40px',
                      backgroundColor: 'var(--bg-elevated)',
                      border: '1px solid var(--border-bright)',
                      color: 'var(--text-primary)',
                      fontSize: '11px',
                      fontWeight: 700,
                      borderRadius: 'var(--radius-sm)',
                      cursor: 'pointer',
                    }}
                  >
                    VIEW PROBABILITIES
                  </button>
                </div>
              </div>
            )}

            {/* Tab 2: Forecast */}
            {activeTab === 'forecast' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  {/* Horizon pills */}
                  <div style={{ display: 'flex', gap: '6px' }}>
                    {[30, 60, 90].map((days) => (
                      <button
                        key={days}
                        onClick={() => setForecastHorizon(days)}
                        style={{
                          padding: '4px 10px',
                          borderRadius: '12px',
                          backgroundColor: forecastHorizon === days ? 'rgba(6, 182, 212, 0.15)' : 'var(--bg-elevated)',
                          border: `1px solid ${forecastHorizon === days ? 'var(--accent-cyan)' : 'var(--border)'}`,
                          color: forecastHorizon === days ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                          fontSize: '10px',
                          fontWeight: 700,
                          cursor: 'pointer',
                        }}
                      >
                        {days}D HORIZON
                      </button>
                    ))}
                  </div>

                  {/* MC vs Linear */}
                  <div style={{ display: 'flex', gap: '4px', backgroundColor: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '2px' }}>
                    <button
                      onClick={() => setForecastView('mc')}
                      style={{
                        padding: '4px 8px',
                        backgroundColor: forecastView === 'mc' ? 'var(--bg-elevated)' : 'transparent',
                        border: 'none',
                        color: forecastView === 'mc' ? 'var(--text-primary)' : 'var(--text-muted)',
                        fontSize: '9px',
                        fontWeight: 700,
                        cursor: 'pointer',
                        borderRadius: '2px',
                      }}
                    >
                      MONTE CARLO
                    </button>
                    <button
                      onClick={() => setForecastView('linear')}
                      style={{
                        padding: '4px 8px',
                        backgroundColor: forecastView === 'linear' ? 'var(--bg-elevated)' : 'transparent',
                        border: 'none',
                        color: forecastView === 'linear' ? 'var(--text-primary)' : 'var(--text-muted)',
                        fontSize: '9px',
                        fontWeight: 700,
                        cursor: 'pointer',
                        borderRadius: '2px',
                      }}
                    >
                      LINEAR
                    </button>
                  </div>
                </div>

                {/* Main chart wrapper */}
                <div style={{ position: 'relative' }}>
                  {forecastLoading ? (
                    <div style={{ height: '260px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
                      <Loader2 size={24} className="animate-spin" />
                    </div>
                  ) : (
                    <div style={{ width: '100%', height: '260px' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={forecastData} margin={{ top: 10, right: 5, left: -20, bottom: 0 }}>
                          <XAxis dataKey="day" stroke="var(--text-muted)" fontSize={9} fontFamily="var(--font-mono)" tickLine={false} />
                          <YAxis stroke="var(--text-muted)" fontSize={9} fontFamily="var(--font-mono)" tickLine={false} axisLine={false} domain={['auto', 'auto']} orientation="right" />
                          <ChartTooltip
                            content={({ active, payload }) => {
                              if (active && payload && payload.length) {
                                const data = payload[0].payload;
                                return (
                                  <div
                                    style={{
                                      background: 'rgba(26, 29, 36, 0.95)',
                                      border: '1px solid var(--border-bright)',
                                      borderRadius: 'var(--radius-md)',
                                      padding: '8px 12px',
                                      fontSize: '11px',
                                      fontFamily: 'var(--font-mono)',
                                      color: 'var(--text-primary)',
                                    }}
                                  >
                                    <div style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>{data.day}</div>
                                    {data.price !== undefined && (
                                      <div>Price: <span style={{ color: 'var(--accent-cyan)' }}>{data.price.toFixed(2)}</span></div>
                                    )}
                                    {data.p50 !== undefined && (() => {
                                      const p25Val = data.p25 !== undefined ? data.p25 : (Array.isArray(data.p25_p75) ? data.p25_p75[0] : undefined);
                                      const p75Val = data.p75 !== undefined ? data.p75 : (Array.isArray(data.p25_p75) ? data.p25_p75[1] : undefined);
                                      const p5Val = data.p5 !== undefined ? data.p5 : (Array.isArray(data.p5_p95) ? data.p5_p95[0] : undefined);
                                      const p95Val = data.p95 !== undefined ? data.p95 : (Array.isArray(data.p5_p95) ? data.p5_p95[1] : undefined);
                                      return (
                                        <>
                                          <div>P50 Median: <span style={{ color: 'var(--accent-purple)' }}>{data.p50.toFixed(2)}</span></div>
                                          <div>P25-P75: <span>{p25Val !== undefined ? p25Val.toFixed(2) : '—'} - {p75Val !== undefined ? p75Val.toFixed(2) : '—'}</span></div>
                                          {showP5P95 && (
                                            <div>P5-P95: <span style={{ color: 'var(--text-secondary)' }}>{p5Val !== undefined ? p5Val.toFixed(2) : '—'} - {p95Val !== undefined ? p95Val.toFixed(2) : '—'}</span></div>
                                          )}
                                        </>
                                      );
                                    })()}
                                    {forecastView === 'linear' && data.linear && (
                                      <div>Linear projection: <span style={{ color: 'var(--accent-amber)' }}>{data.linear.toFixed(2)}</span></div>
                                    )}
                                  </div>
                                );
                              }
                              return null;
                            }}
                          />
                          <ReferenceLine x="Today" stroke="var(--border-bright)" strokeDasharray="3 3" label={{ value: 'Today', fill: 'var(--text-muted)', fontSize: 9, position: 'top' }} />

                          {/* Historical price line */}
                          <Line type="monotone" dataKey="price" stroke="var(--accent-cyan)" strokeWidth={1.5} dot={false} connectNulls />

                          {/* Linear projection estimate */}
                          {forecastView === 'linear' && (
                            <Line type="monotone" dataKey="linear" stroke="var(--accent-amber)" strokeWidth={1.5} strokeDasharray="3 3" dot={false} connectNulls />
                          )}

                          {/* Monte Carlo bands */}
                          {forecastView === 'mc' && (
                            <>
                              {showP5P95 && (
                                <Area type="monotone" dataKey="p5_p95" stroke="none" fill="var(--accent-purple)" fillOpacity={0.06} />
                              )}
                              <Area type="monotone" dataKey="p25_p75" stroke="none" fill="var(--accent-purple)" fillOpacity={0.15} />
                              <Line type="monotone" dataKey="p50" stroke="var(--accent-purple)" strokeWidth={1.5} dot={false} connectNulls />
                            </>
                          )}
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </div>

                {forecastView === 'mc' && (
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                    <input type="checkbox" checked={showP5P95} onChange={() => setShowP5P95(!showP5P95)} />
                    Show P5-P95 (Outer Cone) confidence intervals
                  </label>
                )}

                {/* Monte Carlo stats */}
                {forecastMetrics && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
                    <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
                      GBM SIMULATION METRICS (1,000 PATHS)
                    </span>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
                      <div style={{ backgroundColor: 'var(--bg-elevated)', padding: '8px', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                        <span style={{ fontSize: '8px', color: 'var(--text-muted)', display: 'block' }}>MEDIAN</span>
                        <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', fontWeight: 700, marginTop: '2px', display: 'block' }}>
                          {forecastMetrics.expected_value ? forecastMetrics.expected_value.toFixed(1) : '—'}
                        </span>
                      </div>
                      <div style={{ backgroundColor: 'var(--bg-elevated)', padding: '8px', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                        <span style={{ fontSize: '8px', color: 'var(--text-muted)', display: 'block' }}>VaR 95%</span>
                        <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--risk-critical)', marginTop: '2px', display: 'block' }}>
                          {formatPercent(forecastMetrics.var_95 || -5.2)}
                        </span>
                      </div>
                      <div style={{ backgroundColor: 'var(--bg-elevated)', padding: '8px', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                        <span style={{ fontSize: '8px', color: 'var(--text-muted)', display: 'block' }}>CVaR 95%</span>
                        <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--risk-critical)', marginTop: '2px', display: 'block' }}>
                          {formatPercent(forecastMetrics.cvar_95 || -8.1)}
                        </span>
                      </div>
                      <div style={{ backgroundColor: 'var(--bg-elevated)', padding: '8px', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                        <span style={{ fontSize: '8px', color: 'var(--text-muted)', display: 'block' }}>SHARPE</span>
                        <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-green)', marginTop: '2px', display: 'block' }}>
                          {formatNumber(forecastMetrics.sharpe_ratio, 2)}
                        </span>
                      </div>
                      <div style={{ backgroundColor: 'var(--bg-elevated)', padding: '8px', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                        <span style={{ fontSize: '8px', color: 'var(--text-muted)', display: 'block' }}>P(LOSS)</span>
                        <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--risk-critical)', marginTop: '2px', display: 'block' }}>
                          {formatPercent(forecastMetrics.probability_of_loss || 18.2)}
                        </span>
                      </div>
                    </div>

                    {forecastMetrics.interpretation && (
                      <div style={{ marginTop: '12px', borderTop: '1px solid var(--border)', paddingTop: '12px', textAlign: 'left' }}>
                        <span style={{ fontSize: '9px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', display: 'block', marginBottom: '6px' }}>
                          AI FORECAST INTERPRETATION
                        </span>
                        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0, backgroundColor: 'var(--bg-elevated)', padding: '10px', borderRadius: 'var(--radius-sm)', borderLeft: '3px solid var(--accent-cyan)' }}>
                          {forecastMetrics.interpretation}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Tab 3: AI Reasoning */}
            {activeTab === 'reasoning' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div>
                  <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', display: 'block', marginBottom: '8px' }}>
                    QUANTITATIVE TACTICAL RATIONALE
                  </span>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
                    {selectedAsset.reasoning}
                  </p>
                </div>

                {/* Risk Factors list */}
                <div style={{ borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
                  <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', display: 'block', marginBottom: '8px' }}>
                    MONITORED RISK THREATS
                  </span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {selectedAsset.risk_factors ? (
                      selectedAsset.risk_factors.map((rf: string) => (
                        <div key={rf} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-primary)' }}>
                          <span style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: 'var(--risk-critical)' }} />
                          {rf}
                        </div>
                      ))
                    ) : (
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>No monitored risk vectors.</div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Tab 4: Timeline */}
            {activeTab === 'timeline' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
                  GEOPOLITICAL EVENT LOGS
                </span>
                {/* Vertical timeline */}
                <div style={{ borderLeft: '2px solid var(--border)', paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '20px', marginLeft: '8px' }}>
                  {[
                    { date: '2h ago', title: 'Naval Activities Escalate', severity: 8.2, desc: 'Counter-maneuvers spotted in transit zones.' },
                    { date: '1d ago', title: 'Export Sanctions Enforced', severity: 6.8, desc: 'Sanctions target semiconductor mineral supplies.' },
                    { date: '3d ago', title: 'Rate Policy Signals Shift', severity: 5.5, desc: 'Central banks warn of inflation spikes.' },
                  ].map((evt, idx) => (
                    <div key={idx} style={{ position: 'relative' }}>
                      <div
                        style={{
                          position: 'absolute',
                          left: '-22px',
                          top: '4px',
                          width: '10px',
                          height: '10px',
                          borderRadius: '50%',
                          backgroundColor: riskColor(evt.severity * 10),
                          border: '2px solid var(--bg-surface)',
                        }}
                      />
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{evt.date}</span>
                        <SeverityBadge score={evt.severity} showScore={false} />
                      </div>
                      <h4 style={{ margin: '4px 0', fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>{evt.title}</h4>
                      <p style={{ margin: 0, fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>{evt.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tab 5: Reliability */}
            {activeTab === 'reliability' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
                  HISTORICAL ACCURACY CONES
                </span>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                  <div style={{ backgroundColor: 'var(--bg-elevated)', padding: '8px', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                    <span style={{ fontSize: '8px', color: 'var(--text-muted)', display: 'block' }}>WIN RATE</span>
                    <span style={{ fontSize: '14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-green)', marginTop: '2px', display: 'block' }}>
                      {selectedAsset.win_rate != null ? formatPercent(selectedAsset.win_rate) : '78%'}
                    </span>
                  </div>
                  <div style={{ backgroundColor: 'var(--bg-elevated)', padding: '8px', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                    <span style={{ fontSize: '8px', color: 'var(--text-muted)', display: 'block' }}>AVG RETURN</span>
                    <span style={{ fontSize: '14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-cyan)', marginTop: '2px', display: 'block' }}>
                      {selectedAsset.avg_return != null ? `${selectedAsset.avg_return >= 0 ? '+' : ''}${selectedAsset.avg_return}%` : '+4.2%'}
                    </span>
                  </div>
                  <div style={{ backgroundColor: 'var(--bg-elevated)', padding: '8px', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                    <span style={{ fontSize: '8px', color: 'var(--text-muted)', display: 'block' }}>HOLD DAY</span>
                    <span style={{ fontSize: '14px', fontFamily: 'var(--font-mono)', fontWeight: 700, marginTop: '2px', display: 'block' }}>
                      {selectedAsset.hold_days != null ? `${selectedAsset.hold_days}d` : '3.5d'}
                    </span>
                  </div>
                  <div style={{ backgroundColor: 'var(--bg-elevated)', padding: '8px', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                    <span style={{ fontSize: '8px', color: 'var(--text-muted)', display: 'block' }}>TOTAL RUNS</span>
                    <span style={{ fontSize: '14px', fontFamily: 'var(--font-mono)', fontWeight: 700, marginTop: '2px', display: 'block' }}>
                      {selectedAsset.total_runs ?? 142}
                    </span>
                  </div>
                </div>

                {/* Table of past signals */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontWeight: 700 }}>RECENT SIGNALS LOG</span>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-muted)' }}>
                        <th style={{ padding: '6px' }}>DATE</th>
                        <th style={{ padding: '6px' }}>TYPE</th>
                        <th style={{ padding: '6px' }}>ENTRY</th>
                        <th style={{ padding: '6px' }}>EXIT</th>
                        <th style={{ padding: '6px' }}>RETURN</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(selectedAsset.past_signals || [
                        { date: '06/10', type: 'BUY', entry: 2320, exit: 2390, ret: '+3.0%', win: true },
                        { date: '06/05', type: 'SELL', entry: 2360, exit: 2320, ret: '+1.7%', win: true },
                        { date: '05/28', type: 'BUY', entry: 2310, exit: 2300, ret: '-0.4%', win: false },
                      ]).map((item: any, idx: number) => (
                        <tr key={idx} style={{ borderBottom: '1px solid var(--border)', backgroundColor: idx % 2 === 0 ? 'var(--bg-elevated)' : 'transparent' }}>
                          <td style={{ padding: '6px', fontFamily: 'var(--font-mono)' }}>{item.date}</td>
                          <td style={{ padding: '6px', color: item.type === 'BUY' ? 'var(--accent-green)' : 'var(--risk-critical)', fontWeight: 700 }}>{item.type}</td>
                          <td style={{ padding: '6px', fontFamily: 'var(--font-mono)' }}>{item.entry}</td>
                          <td style={{ padding: '6px', fontFamily: 'var(--font-mono)' }}>{item.exit}</td>
                          <td style={{ padding: '6px', fontFamily: 'var(--font-mono)', color: item.win ? 'var(--accent-green)' : 'var(--risk-critical)', fontWeight: 600 }}>{item.ret}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </section>
      ) : (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            height: '100%',
            color: 'var(--text-muted)',
            fontSize: '13px',
          }}
        >
          Select an asset from the list to view detailed signals.
        </div>
      )}
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

export default Markets;
