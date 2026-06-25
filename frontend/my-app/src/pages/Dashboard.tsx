import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import Globe from 'react-globe.gl';
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet';
import { useGTI } from '../hooks/useGTI';
import { useSignals } from '../hooks/useSignals';
import { riskColor } from '../utils/risk';
import { formatCurrency } from '../utils/format';
import { RiskGauge } from '../components/ui/RiskGauge';
import { Sparkline } from '../components/ui/Sparkline';
import { SignalPill } from '../components/ui/SignalPill';
import { ConfidenceBar } from '../components/ui/ConfidenceBar';
import { LiveDot } from '../components/ui/LiveDot';
import {
  Settings,
  ChevronRight,
  Cpu,
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

// Country coordinate mapping for 3D Globe capital markers
const CAPITAL_COORDS: Record<string, { lat: number; lon: number; name: string }> = {
  US: { lat: 38.9072, lon: -77.0369, name: 'Washington D.C.' },
  CN: { lat: 39.9042, lon: 116.4074, name: 'Beijing' },
  TW: { lat: 25.0330, lon: 121.5654, name: 'Taipei' },
  RU: { lat: 55.7558, lon: 37.6173, name: 'Moscow' },
  UA: { lat: 50.4501, lon: 30.5234, name: 'Kyiv' },
  SA: { lat: 24.7136, lon: 46.6753, name: 'Riyadh' },
  IR: { lat: 35.6892, lon: 51.3890, name: 'Tehran' },
  IL: { lat: 31.7683, lon: 35.2137, name: 'Jerusalem' },
};

// Risk score â†’ hex color string
const riskHexStr = (score: number): string => {
  if (score >= 80) return '#ef4444';  // CRITICAL â€“ red
  if (score >= 60) return '#f59e0b';  // HIGH â€“ amber
  if (score >= 35) return '#3b82f6';  // MEDIUM â€“ blue
  return '#22c55e';                   // LOW â€“ green
};

const riskLabel = (score: number): string => {
  if (score >= 80) return 'CRITICAL';
  if (score >= 60) return 'HIGH';
  if (score >= 35) return 'MEDIUM';
  return 'LOW';
};

// â”€â”€ GeoRiskGlobe â€” react-globe.gl powered globe with country risk coloring â”€â”€
interface GeoRiskGlobeProps {
  globeData: any[];
  onCountryClick: (code: string) => void;
  windowWidth: number;
}

const GeoRiskGlobe: React.FC<GeoRiskGlobeProps> = ({ globeData, onCountryClick, windowWidth }) => {
  const globeEl = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [countries, setCountries] = useState<any>({ features: [] });
  const [hoveredFeature, setHoveredFeature] = useState<any>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [dimensions, setDimensions] = useState({ w: 0, h: 0 });

  // Load GeoJSON once
  useEffect(() => {
    fetch('/countries.geojson')
      .then((r) => r.json())
      .then((data) => setCountries(data))
      .catch(() => console.warn('GeoRiskGlobe: could not load countries.geojson'));
  }, []);

  // Sync container dimensions
  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDimensions({ w: Math.floor(width), h: Math.floor(height) });
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  // Auto-rotate â€“ stop when user interacts
  useEffect(() => {
    if (!globeEl.current) return;
    globeEl.current.controls().autoRotate = true;
    globeEl.current.controls().autoRotateSpeed = 0.5;
    globeEl.current.controls().enableZoom = true;
    globeEl.current.controls().minDistance = 180;
    globeEl.current.controls().maxDistance = 600;
    // Start with a nice angle
    globeEl.current.pointOfView({ lat: 20, lng: 10, altitude: 2.0 }, 0);
  }, [dimensions]); // re-run after dimensions settle

  // Build a lookup from ISO-A2 â†’ risk data
  const riskMap = React.useMemo(() => {
    const m: Record<string, any> = {};
    globeData.forEach((c) => { if (c.country_code) m[c.country_code.toUpperCase()] = c; });
    return m;
  }, [globeData]);

  const getCountryRisk = useCallback((feat: any): any | null => {
    const iso2 = (feat?.properties?.iso_a2 || feat?.properties?.ISO_A2 || '').toUpperCase();
    return riskMap[iso2] ?? null;
  }, [riskMap]);

  // Polygon fill color
  const polygonColor = useCallback((feat: any) => {
    if (feat === hoveredFeature) {
      const risk = getCountryRisk(feat);
      const base = risk ? riskHexStr(risk.risk_score) : '#334155';
      return base + 'ee'; // brighter on hover
    }
    const risk = getCountryRisk(feat);
    if (!risk) return 'rgba(51,65,85,0.35)'; // unmapped country
    const hex = riskHexStr(risk.risk_score);
    // Convert to rgba with lower alpha for normal state
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},0.55)`;
  }, [hoveredFeature, getCountryRisk]);

  // Polygon side color (border)
  const polygonSideColor = useCallback((feat: any) => {
    const risk = getCountryRisk(feat);
    if (!risk) return 'rgba(100,116,139,0.2)';
    return riskHexStr(risk.risk_score) + '55';
  }, [getCountryRisk]);

  // Polygon stroke color
  const polygonStrokeColor = useCallback((feat: any) => {
    if (feat === hoveredFeature) return '#ffffff';
    const risk = getCountryRisk(feat);
    if (!risk) return 'rgba(100,116,139,0.3)';
    return riskHexStr(risk.risk_score) + '99';
  }, [hoveredFeature, getCountryRisk]);

  const handlePolygonHover = useCallback((feat: any) => {
    setHoveredFeature(feat);
  }, []);

  const handlePolygonClick = useCallback((feat: any) => {
    const iso2 = (feat?.properties?.iso_a2 || feat?.properties?.ISO_A2 || '').toUpperCase();
    if (iso2 && iso2 !== '-99' && iso2 !== '-9') onCountryClick(iso2);
  }, [onCountryClick]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    setTooltipPos({ x: e.clientX - rect.left + 16, y: e.clientY - rect.top - 10 });
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener('mousemove', handleMouseMove);
    return () => el.removeEventListener('mousemove', handleMouseMove);
  }, [handleMouseMove]);

  const hoveredRisk = hoveredFeature ? getCountryRisk(hoveredFeature) : null;
  const hoveredName = hoveredFeature?.properties?.name || hoveredFeature?.properties?.NAME || '';
  const hoveredLabel = hoveredRisk ? riskLabel(hoveredRisk.risk_score) : null;

  // Arc data for geopolitical tension routes
  const arcsData = React.useMemo(() => [
    { startLat: 38.9, startLng: -77.0,  endLat: 25.0, endLng: 121.6, color: ['#06b6d4', '#06b6d4'] }, // USâ†’TW
    { startLat: 55.8, startLng: 37.6,   endLat: 50.5, endLng: 30.5,  color: ['#ef4444', '#ef4444'] }, // RUâ†’UA
    { startLat: 39.9, startLng: 116.4,  endLat: 25.0, endLng: 121.6, color: ['#f59e0b', '#f59e0b'] }, // CNâ†’TW
    { startLat: 24.7, startLng: 46.7,   endLat: 35.7, endLng: 51.4,  color: ['#f59e0b', '#f59e0b'] }, // SAâ†’IR
  ], []);

  return (
    <div
      ref={containerRef}
      style={{ position: 'relative', width: '100%', height: '100%', minHeight: '340px', overflow: 'hidden' }}
    >
      {dimensions.w > 0 && (
        <Globe
          ref={globeEl}
          width={dimensions.w}
          height={dimensions.h || 420}
          backgroundColor="rgba(0,0,0,0)"
          // Globe appearance
          globeImageUrl="//unpkg.com/three-globe/example/img/earth-night.jpg"
          bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
          atmosphereColor="#3b82f6"
          atmosphereAltitude={0.18}
          // Country polygons
          polygonsData={countries.features}
          polygonAltitude={(feat: any) => feat === hoveredFeature ? 0.014 : 0.006}
          polygonCapColor={polygonColor}
          polygonSideColor={polygonSideColor}
          polygonStrokeColor={polygonStrokeColor}
          polygonLabel={() => ''}
          onPolygonHover={handlePolygonHover}
          onPolygonClick={handlePolygonClick}
          polygonsTransitionDuration={200}
          // Tension arcs
          arcsData={arcsData}
          arcColor={(d: any) => d.color}
          arcDashLength={0.4}
          arcDashGap={0.15}
          arcDashAnimateTime={2000}
          arcAltitude={0.25}
          arcStroke={0.5}
          arcAltitudeAutoScale={0.3}
        />
      )}

      {/* Country Hover Tooltip */}
      {hoveredFeature && (
        <div
          style={{
            position: 'absolute',
            left: `${tooltipPos.x}px`,
            top: `${tooltipPos.y}px`,
            pointerEvents: 'none',
            backgroundColor: 'rgba(10,13,20,0.92)',
            border: `1px solid ${
              hoveredLabel === 'CRITICAL' ? '#ef4444' :
              hoveredLabel === 'HIGH' ? '#f59e0b' :
              hoveredLabel === 'MEDIUM' ? '#06b6d4' :
              hoveredRisk ? '#22c55e' : '#334155'
            }`,
            borderRadius: '8px',
            padding: '10px 14px',
            backdropFilter: 'blur(12px)',
            zIndex: 20,
            minWidth: '180px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          }}
        >
          <div style={{ fontWeight: 700, fontSize: '13px', color: '#f1f5f9', marginBottom: '6px' }}>
            {hoveredRisk?.country_name || hoveredName}
          </div>
          {hoveredRisk ? (
            <>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 600 }}>RISK SCORE</span>
                <span style={{
                  fontFamily: 'monospace', fontWeight: 700, fontSize: '15px',
                  color: hoveredLabel === 'CRITICAL' ? '#ef4444' :
                         hoveredLabel === 'HIGH' ? '#f59e0b' :
                         hoveredLabel === 'MEDIUM' ? '#06b6d4' : '#22c55e',
                }}>
                  {hoveredRisk.risk_score.toFixed(1)}
                </span>
              </div>
              <span style={{
                display: 'inline-block', fontSize: '9px', fontWeight: 700,
                letterSpacing: '0.06em', padding: '2px 7px', borderRadius: '4px',
                backgroundColor:
                  hoveredLabel === 'CRITICAL' ? 'rgba(239,68,68,0.15)' :
                  hoveredLabel === 'HIGH' ? 'rgba(245,158,11,0.15)' :
                  hoveredLabel === 'MEDIUM' ? 'rgba(6,182,212,0.15)' : 'rgba(34,197,94,0.15)',
                color:
                  hoveredLabel === 'CRITICAL' ? '#ef4444' :
                  hoveredLabel === 'HIGH' ? '#f59e0b' :
                  hoveredLabel === 'MEDIUM' ? '#06b6d4' : '#22c55e',
              }}>
                {hoveredLabel}
              </span>
            </>
          ) : (
            <span style={{ fontSize: '10px', color: '#64748b' }}>No risk data</span>
          )}
          {hoveredRisk && (
            <div style={{ marginTop: '8px', fontSize: '10px', color: '#64748b' }}>
              â†— Click to view details
            </div>
          )}
        </div>
      )}

      {/* Risk Legend */}
      <div style={{
        position: 'absolute', bottom: '10px', right: '10px',
        display: 'flex', flexDirection: 'column', gap: '4px',
        padding: '8px 10px',
        backgroundColor: 'rgba(10,13,20,0.82)',
        borderRadius: '8px',
        border: '1px solid rgba(255,255,255,0.08)',
        backdropFilter: 'blur(8px)',
        zIndex: 10,
      }}>
        {[
          { l: 'CRITICAL', c: '#ef4444' },
          { l: 'HIGH',     c: '#f59e0b' },
          { l: 'MEDIUM',   c: '#3b82f6' },
          { l: 'LOW',      c: '#22c55e' },
        ].map(({ l, c }) => (
          <div key={l} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: c }} />
            <span style={{ fontSize: '9px', fontWeight: 700, color: '#94a3b8', letterSpacing: '0.05em' }}>{l}</span>
          </div>
        ))}
      </div>
    </div>
  );
};





// Main Dashboard Page
export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const gti = useGTI();
  const { signals, loading: signalsLoading } = useSignals(); // Seeded signals and WS updates

  // Local Page States
  const [countriesBreakdown, setCountriesBreakdown] = useState<any[]>([]);
  const [topRiskCountries, setTopRiskCountries] = useState<any[]>([]);
  const [globeData, setGlobeData] = useState<any[]>([]);
  const [markets, setMarkets] = useState<any[]>([]);
  const [pinnedMarkets, setPinnedMarkets] = useState<string[]>(['GOLD', 'OIL_BRENT', 'SP500', 'BTCUSD']);
  const [customizeOpen, setCustomizeOpen] = useState<boolean>(false);
  const [windowWidth, setWindowWidth] = useState<number>(window.innerWidth);
  const [dashboardLoading, setDashboardLoading] = useState<boolean>(true);

  // Time since last update timer
  const [secondsSinceUpdate, setSecondsSinceUpdate] = useState<number>(0);
  const lastUpdateRef = useRef<number>(Date.now());

  // Listen for width resize
  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Update timer ticks
  useEffect(() => {
    const interval = setInterval(() => {
      const diff = Math.floor((Date.now() - lastUpdateRef.current) / 1000);
      setSecondsSinceUpdate(diff);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Reset timer on GTI WS updates
  useEffect(() => {
    if (gti) {
      lastUpdateRef.current = Date.now();
      setSecondsSinceUpdate(0);
    }
  }, [gti]);

  // Fetch breakdown & globe data
  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        const countryRiskRes = await axios.get(`${API_BASE}/risk/countries`);
        if (countryRiskRes.data) {
          const list = countryRiskRes.data;
          // Calculate tiers
          const critical = list.filter((c: any) => c.risk_score >= 80).length;
          const high = list.filter((c: any) => c.risk_score >= 60 && c.risk_score < 80).length;
          const medium = list.filter((c: any) => c.risk_score >= 35 && c.risk_score < 60).length;
          const low = list.filter((c: any) => c.risk_score < 35).length;
          setCountriesBreakdown([
            { label: 'CRITICAL', count: critical, color: 'var(--risk-critical)' },
            { label: 'HIGH', count: high, color: 'var(--accent-amber)' },
            { label: 'MEDIUM', count: medium, color: 'var(--accent-cyan)' },
            { label: 'LOW', count: low, color: 'var(--risk-low)' },
          ]);

          // Sort and select top 5 highest risk countries
          const sorted = [...list]
            .sort((a: any, b: any) => b.risk_score - a.risk_score)
            .slice(0, 5);
          setTopRiskCountries(sorted);
        }

        const globeRes = await axios.get(`${API_BASE}/risk/globe`);
        if (globeRes.data) {
          setGlobeData(globeRes.data);
        }

        const marketRes = await axios.get(`${API_BASE}/market/all-with-signals`);
        if (marketRes.data) {
          setMarkets(marketRes.data);
        }
      } catch (err) {
        console.warn('Failed to load dashboard data from API, using default mock structures:', err);
        // Fallback default mock counts
        setCountriesBreakdown([
          { label: 'CRITICAL', count: 12, color: 'var(--risk-critical)' },
          { label: 'HIGH', count: 28, color: 'var(--accent-amber)' },
          { label: 'MEDIUM', count: 19, color: 'var(--accent-cyan)' },
          { label: 'LOW', count: 43, color: 'var(--risk-low)' },
        ]);
        setTopRiskCountries([
          { country_code: 'UA', country_name: 'Ukraine', risk_score: 90.0 },
          { country_code: 'TW', country_name: 'Taiwan', risk_score: 82.0 },
          { country_code: 'RU', country_name: 'Russia', risk_score: 78.0 },
          { country_code: 'IL', country_name: 'Israel', risk_score: 75.0 },
          { country_code: 'IR', country_name: 'Iran', risk_score: 72.0 },
        ]);
        // Fallback default mock globe capitals
        setGlobeData([
          { country_code: 'US', country_name: 'United States', risk_score: 25.0, color_code: 'Green' },
          { country_code: 'CN', country_name: 'China', risk_score: 65.0, color_code: 'Red' },
          { country_code: 'TW', country_name: 'Taiwan', risk_score: 82.0, color_code: 'Red' },
          { country_code: 'RU', country_name: 'Russia', risk_score: 78.0, color_code: 'Red' },
          { country_code: 'UA', country_name: 'Ukraine', risk_score: 90.0, color_code: 'Red' },
          { country_code: 'SA', country_name: 'Saudi Arabia', risk_score: 45.0, color_code: 'Yellow' },
          { country_code: 'IR', country_name: 'Iran', risk_score: 72.0, color_code: 'Red' },
          { country_code: 'IL', country_name: 'Israel', risk_score: 75.0, color_code: 'Red' },
        ]);
      } finally {
        setDashboardLoading(false);
      }
    };
    loadDashboardData();
  }, []);

  const handleCountryClick = (code: string) => {
    // country_code from GeoJSON mesh (ISO-2). Map page handles both id and ISO code lookups.
    const country = globeData.find(
      (c) => c.country_code?.toUpperCase() === code?.toUpperCase()
    );
    // Prefer DB id so the Map page auto-opens the details panel; fall back to ISO code
    navigate(`/map?country=${country?.id ?? code}&view=2d`);
  };

  const handleTogglePin = (symbol: string) => {
    setPinnedMarkets((prev) => {
      if (prev.includes(symbol)) {
        if (prev.length <= 1) return prev; // must keep at least 1
        return prev.filter((s) => s !== symbol);
      } else {
        if (prev.length >= 6) return prev; // max 6
        return [...prev, symbol];
      }
    });
  };

  // Featured signal computes as the highest confidence signal
  const featuredSignal = signals.length > 0
    ? [...signals].sort((a, b) => b.confidence - a.confidence)[0]
    : null;

  // Check hardware concurrency to trigger 2D fallback map
  const isPerformanceLow = navigator.hardwareConcurrency !== undefined && navigator.hardwareConcurrency < 4;

  // Filter signals list to render inside right rail
  const renderedSignalsList = signals.slice(0, 10);

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: windowWidth >= 1440 ? '240px 1fr 320px' : '240px 1fr',
        gap: '20px',
        padding: '20px',
        height: 'calc(100vh - 104px)', // 56px Nav + 48px StatusBar = 104px
        boxSizing: 'border-box',
        overflow: 'hidden',
      }}
    >
      {/* LEFT COLUMN: GTI Deep Dive */}
      <aside
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '24px',
          overflowY: 'auto',
          paddingRight: '4px',
        }}
      >
        {/* Risk Gauge */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px',
            textAlign: 'center',
          }}
        >
          <span
            style={{
              fontSize: '10px',
              fontWeight: 700,
              color: 'var(--text-muted)',
              letterSpacing: '0.08em',
              display: 'block',
              marginBottom: '12px',
            }}
          >
            GLOBAL TENSION INDEX
          </span>
          <RiskGauge score={gti?.score ?? 68.5} size={180} />
          <span
            style={{
              fontSize: '11px',
              color: 'var(--text-muted)',
              display: 'block',
              marginTop: '12px',
            }}
          >
            Updated {secondsSinceUpdate}s ago
          </span>
        </div>

        {/* Risk Level Breakdown */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
            RISK EXPOSURE TIERS
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {countriesBreakdown.map((row) => (
              <div key={row.label} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: row.color }} />
                    <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{row.label}</span>
                  </div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {row.count} countries
                  </span>
                </div>
                {/* Visual bar */}
                <div style={{ height: '3px', width: '100%', backgroundColor: 'var(--bg-elevated)', borderRadius: '2px' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${Math.min(100, (row.count / 95) * 100)}%`, // out of 95 mock countries max
                      backgroundColor: row.color,
                      borderRadius: '2px',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 30-Day GTI Sparkline */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
            30-DAY GTI HISTORY
          </span>
          <Sparkline
            data={gti?.trend ? gti.trend.slice(-30) : [62, 63, 65, 68, 67, 68.5]}
            color="amber"
            height={60}
          />
        </div>

        {/* Top Risk Countries */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            flex: 1,
            minHeight: '220px',
          }}
        >
          <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
            TOP RISK COUNTRIES
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto', flex: 1 }}>
            {topRiskCountries.length > 0 ? (
              topRiskCountries.map((c) => {
                const scoreColor = riskColor(c.risk_score);
                return (
                  <div
                    key={c.country_code}
                    onClick={() => handleCountryClick(c.country_code)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 10px',
                      backgroundColor: 'var(--bg-elevated)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-md)',
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
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: scoreColor }} />
                      <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {c.country_name}
                      </span>
                      <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                        {c.country_code}
                      </span>
                    </div>
                    <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: scoreColor }}>
                      {c.risk_score.toFixed(1)}
                    </span>
                  </div>
                );
              })
            ) : (
              <div className="skeleton" style={{ width: '100%', height: '100%', minHeight: '140px', borderRadius: 'var(--radius-md)' }} />
            )}
          </div>
        </div>
      </aside>

      {/* CENTER COLUMN: Central War Room */}
      <main
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
        {/* Pinned Market Tickers Strip */}
        <div
          style={{
            height: '64px',
            width: '100%',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 16px',
            boxSizing: 'border-box',
            backgroundColor: 'var(--bg-base)',
          }}
        >
          <div style={{ display: 'flex', gap: '16px', overflowX: 'auto', flex: 1, marginRight: '16px' }}>
            {dashboardLoading ? (
              Array.from({ length: 4 }).map((_, idx) => (
                <div
                  key={`ticker-skeleton-${idx}`}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                    minWidth: '130px',
                    padding: '4px 8px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div className="skeleton" style={{ width: '50px', height: '12px' }} />
                    <div className="skeleton" style={{ width: '30px', height: '12px' }} />
                  </div>
                  <div className="skeleton" style={{ width: '80px', height: '16px', marginTop: '6px' }} />
                </div>
              ))
            ) : (
              pinnedMarkets.map((sym) => {
                const market = markets.find((m) => m.symbol === sym);
                const price = market?.price ?? 100.0;
                // Mock ticker fluctuations for preview
                const delta = market?.symbol === 'GOLD' ? 0.45 : market?.symbol === 'OIL_BRENT' ? -1.2 : 0.85;

                return (
                  <div
                    key={sym}
                    onClick={() => navigate(`/markets?asset=${sym}`)}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'center',
                      minWidth: '130px',
                      cursor: 'pointer',
                      padding: '4px 8px',
                      borderRadius: 'var(--radius-sm)',
                      transition: 'background 150ms ease',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{sym}</span>
                      <span
                        style={{
                          fontSize: '10px',
                          fontFamily: 'var(--font-mono)',
                          color: delta > 0 ? 'var(--accent-green)' : 'var(--risk-critical)',
                          fontWeight: 600,
                        }}
                      >
                        {delta > 0 ? '+' : ''}
                        {delta}%
                      </span>
                    </div>
                    <span style={{ fontSize: '14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
                      {formatCurrency(price)}
                    </span>
                  </div>
                );
              })
            )}
          </div>

          {/* Customize Pinned Tickers Picker */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setCustomizeOpen(!customizeOpen)}
              style={{
                backgroundColor: 'var(--bg-elevated)',
                border: '1px solid var(--border-bright)',
                color: 'var(--text-secondary)',
                fontSize: '10px',
                fontWeight: 700,
                padding: '6px 12px',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <Settings size={12} />
              CUSTOMIZE
            </button>

            {customizeOpen && (
              <>
                <div
                  onClick={() => setCustomizeOpen(false)}
                  style={{ position: 'fixed', inset: 0, zIndex: 101 }}
                />
                <div
                  style={{
                    position: 'absolute',
                    right: 0,
                    top: '28px',
                    width: '180px',
                    backgroundColor: 'var(--bg-elevated)',
                    border: '1px solid var(--border-bright)',
                    borderRadius: 'var(--radius-md)',
                    padding: '10px',
                    boxShadow: 'var(--shadow)',
                    zIndex: 102,
                    maxHeight: '220px',
                    overflowY: 'auto',
                  }}
                >
                  <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px' }}>
                    SELECT PINNED ASSETS (MAX 6)
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {['GOLD', 'OIL_BRENT', 'SP500', 'BTCUSD', 'LMT', 'HSI', 'XAUUSD', 'WTI'].map((sym) => {
                      const isPinned = pinnedMarkets.includes(sym);
                      return (
                        <label
                          key={sym}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            fontSize: '11px',
                            cursor: 'pointer',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={isPinned}
                            disabled={!isPinned && pinnedMarkets.length >= 6}
                            onChange={() => handleTogglePin(sym)}
                            style={{ cursor: 'pointer' }}
                          />
                          <span style={{ fontFamily: 'var(--font-mono)' }}>{sym}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Risk Globe â€” react-globe.gl with country risk coloring */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <GeoRiskGlobe
            globeData={globeData}
            onCountryClick={handleCountryClick}
            windowWidth={windowWidth}
          />
        </div>
      </main>

      {/* RIGHT COLUMN: Live Signals Rail */}
      {windowWidth >= 1440 && (
        <aside
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
            overflowY: 'auto',
            paddingRight: '4px',
          }}
        >
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span
              style={{
                fontSize: '12px',
                fontWeight: 700,
                color: 'var(--text-primary)',
                letterSpacing: '0.04em',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <LiveDot />
              LIVE SIGNALS FEED
            </span>
          </div>

          {/* Featured Signal Card */}
          {signalsLoading ? (
            <div
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div className="skeleton" style={{ width: '80px', height: '18px' }} />
                <div className="skeleton" style={{ width: '40px', height: '18px' }} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', margin: '4px 0' }}>
                <div className="skeleton" style={{ width: '100px', height: '12px' }} />
                <div className="skeleton" style={{ width: '140px', height: '20px' }} />
              </div>
              <div style={{ borderTop: '1px solid var(--border)', paddingTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div className="skeleton" style={{ width: '100%', height: '8px' }} />
                <div className="skeleton" style={{ width: '100%', height: '8px' }} />
              </div>
              <div className="skeleton" style={{ width: '100%', height: '36px', borderRadius: 'var(--radius-sm)', marginTop: '6px' }} />
            </div>
          ) : featuredSignal ? (
            <div
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-bright)',
                borderRadius: 'var(--radius-lg)',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                    fontSize: '15px',
                  }}
                >
                  {featuredSignal.market_symbol}
                </span>
                <SignalPill direction={featuredSignal.signal_type} size="sm" />
              </div>

              <div>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600 }}>CURRENT PRICE</span>
                <div style={{ fontSize: '20px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
                  {formatCurrency(featuredSignal.market_price || featuredSignal.entry_price)}
                </div>
              </div>

              <div style={{ borderTop: '1px solid var(--border)', paddingTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <ConfidenceBar label="CONFIDENCE" value={Math.round(featuredSignal.confidence * 100)} color="green" />
                <ConfidenceBar label="UNCERTAINTY" value={Math.round(featuredSignal.uncertainty * 100)} color="amber" />
              </div>

              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.5, borderTop: '1px solid var(--border)', paddingTop: '10px' }}>
                <span style={{ fontWeight: 700, color: 'var(--accent-cyan)', display: 'block', marginBottom: '2px' }}>AI STRATEGY ANALYSIS</span>
                {featuredSignal.reasoning}
              </div>

              <button
                onClick={() => navigate(`/markets?asset=${featuredSignal.market_symbol}`)}
                style={{
                  width: '100%',
                  height: '36px',
                  backgroundColor: 'var(--bg-elevated)',
                  border: '1px solid var(--border-bright)',
                  color: 'var(--accent-cyan)',
                  fontSize: '11px',
                  fontWeight: 700,
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  marginTop: '6px',
                }}
              >
                VIEW FULL REPORT
                <ChevronRight size={12} />
              </button>
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: '11px', textAlign: 'center', padding: '24px 0' }}>
              No featured signals active.
            </div>
          )}

          {/* List of other signals */}
          {signalsLoading ? (
            <div
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                padding: '16px',
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
              }}
            >
              <div className="skeleton" style={{ width: '120px', height: '12px', marginBottom: '12px' }} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {Array.from({ length: 6 }).map((_, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <div className="skeleton" style={{ width: '50px', height: '12px' }} />
                      <div className="skeleton" style={{ width: '80px', height: '10px' }} />
                    </div>
                    <div className="skeleton" style={{ width: '60px', height: '16px' }} />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div
              style={{
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              padding: '16px',
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: '12px' }}>
              ALL ACTIVE SIGNALS ({signals.length})
            </span>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '1px',
                backgroundColor: 'var(--border)',
                overflowY: 'auto',
                borderRadius: 'var(--radius-md)',
              }}
            >
              {renderedSignalsList.map((sig) => (
                <div
                  key={sig.id}
                  onClick={() => navigate(`/markets?asset=${sig.market_symbol}`)}
                  style={{
                    backgroundColor: 'var(--bg-surface)',
                    padding: '8px 12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    transition: 'background 150ms ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-surface)')}
                >
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {sig.market_symbol}
                    </span>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                      {sig.market_name ? sig.market_name.substring(0, 15) : 'Asset'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <SignalPill direction={sig.signal_type} size="sm" />
                    <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', fontWeight: 600 }}>
                      {Math.round(sig.confidence * 100)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          )}
        </aside>
      )}
    </div>
  );
};

export default Dashboard;
