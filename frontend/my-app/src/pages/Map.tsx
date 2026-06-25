import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import L from 'leaflet';
import { useWebSocket } from '../context/WebSocketContext';
import { riskColor, riskLabel } from '../utils/risk';
import { formatCurrency, formatRelativeTime } from '../utils/format';
import { CandlestickChart } from '../components/ui/CandlestickChart';
import { SeverityBadge } from '../components/ui/SeverityBadge';
import { LiveDot } from '../components/ui/LiveDot';
import {
  Filter,
  Search,
  ChevronLeft,
  X,
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

// Country coordinate mapping for flying
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

// Helper to convert ISO-2 code to Flag Emoji
const getFlagEmoji = (countryCode: string) => {
  if (!countryCode) return '';
  const codePoints = countryCode
    .toUpperCase()
    .split('')
    .map((char) => 127397 + char.charCodeAt(0));
  return String.fromCodePoint(...codePoints);
};

// Map Fly controller component to hook into Leaflet context
const MapFlyController: React.FC<{ centroid: [number, number] | null }> = ({ centroid }) => {
  const map = useMap();
  useEffect(() => {
    if (centroid) {
      map.flyTo(centroid, 4, { duration: 1.2 });
    }
  }, [centroid, map]);
  return null;
};

export const Map: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const countryParam = searchParams.get('country');

  // API State
  const [countriesList, setCountriesList] = useState<any[]>([]);
  const [geoJsonData, setGeoJsonData] = useState<any>(null);
  const [selectedCountry, setSelectedCountry] = useState<any | null>(null);
  const [countryEvents, setCountryEvents] = useState<any[]>([]);
  const [countryMarkets, setCountryMarkets] = useState<any[]>([]);
  const [selectedMarket, setSelectedMarket] = useState<any | null>(null);
  const [marketHistory, setMarketHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);
  const [isFallback, setIsFallback] = useState<boolean>(false);
  const [marketContext, setMarketContext] = useState<Record<string, string>>({});

  // Search, Filters & Timelines
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showSearchResults, setShowSearchResults] = useState<boolean>(false);
  const [filterExpanded, setFilterExpanded] = useState<boolean>(true);
  const [selectedRiskFilters, setSelectedRiskFilters] = useState<string[]>(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']);
  const [selectedThemes, setSelectedThemes] = useState<string[]>([]);
  const [flyCentroid, setFlyCentroid] = useState<[number, number] | null>(null);

  // Memoized country lookup record for O(1) style & tooltip updates (avoids Map class name conflict)
  const countryLookupMap = React.useMemo(() => {
    const lookup: Record<string, any> = {};
    countriesList.forEach((c) => {
      if (c.country_code) {
        lookup[c.country_code.toUpperCase()] = c;
      }
      if (c.country_name) {
        lookup[c.country_name.toLowerCase()] = c;
      }
    });
    return lookup;
  }, [countriesList]);

  const geoJsonLayerRef = useRef<L.GeoJSON | null>(null);
  const countriesListRef = useRef<any[]>([]);
  const getStyleForFeatureRef = useRef<any>(null);
  const { subscribe, unsubscribe } = useWebSocket();

  // Sync ref with countriesList to avoid stale closures in Leaflet events
  useEffect(() => {
    countriesListRef.current = countriesList;
  }, [countriesList]);

  // 1. Fetch standard GeoJSON country boundaries from local public folder
  useEffect(() => {
    const fetchGeoJson = async () => {
      try {
        const res = await axios.get('/countries.geojson');
        setGeoJsonData(res.data);
      } catch (err) {
        console.error('Failed to load world GeoJSON boundary file:', err);
      }
    };
    fetchGeoJson();
  }, []);

  // 2. Fetch country risks on mount & WebSocket listeners
  useEffect(() => {
    const fetchCountryRisks = async () => {
      try {
        const res = await axios.get(`${API_BASE}/risk/countries`);
        setCountriesList(res.data || []);
      } catch (err) {
        console.warn('Failed to load country risks, using mock values:', err);
        // Fallback default mock countries
        setCountriesList([
          { id: 1, country_code: 'US', country_name: 'United States', risk_score: 25.0, color_code: 'Green', sector_exposure: { Tech: 45, Finance: 30 } },
          { id: 2, country_code: 'CN', country_name: 'China', risk_score: 65.0, color_code: 'Red', sector_exposure: { Manufacturing: 40, Tech: 35 } },
          { id: 3, country_code: 'TW', country_name: 'Taiwan', risk_score: 82.0, color_code: 'Red', sector_exposure: { Semiconductors: 85 } },
          { id: 4, country_code: 'RU', country_name: 'Russia', risk_score: 78.0, color_code: 'Red', sector_exposure: { Energy: 65 } },
          { id: 5, country_code: 'UA', country_name: 'Ukraine', risk_score: 90.0, color_code: 'Red', sector_exposure: { Agriculture: 50 } },
          { id: 6, country_code: 'SA', country_name: 'Saudi Arabia', risk_score: 45.0, color_code: 'Yellow', sector_exposure: { Energy: 90 } },
          { id: 7, country_code: 'IR', country_name: 'Iran', risk_score: 72.0, color_code: 'Red', sector_exposure: { Energy: 70 } },
          { id: 8, country_code: 'IL', country_name: 'Israel', risk_score: 75.0, color_code: 'Red', sector_exposure: { Tech: 40 } },
        ]);
      }
    };
    fetchCountryRisks();

    // Subscribe to live risk updates
    const subId = subscribe('risk_update', (msg: any) => {
      if (msg.country_id && msg.risk_score) {
        setCountriesList((prev) =>
          prev.map((c) =>
            c.id === msg.country_id || c.country_code === msg.country_id
              ? { ...c, risk_score: msg.risk_score }
              : c
          )
        );
      }
    });

    return () => unsubscribe(subId);
  }, []);

  // 3. Monitor countryParam shifts (e.g. from Dashboard or Search)
  useEffect(() => {
    if (countryParam && countriesList.length > 0) {
      // Lookup by ID or ISO Code
      const country = countriesList.find(
        (c) =>
          c.id.toString() === countryParam ||
          c.country_code.toUpperCase() === countryParam.toUpperCase()
      );
      if (country) {
        setSelectedCountry(country);
        fetchCountryDetails(country.id, country.country_code);
      }
    }
  }, [countryParam, countriesList]);

  // Helper: Fetch country specific events & linked assets
  const fetchCountryDetails = async (countryId: number, countryCode: string) => {
    try {
      // Fetch top risks
      const eventRes = await axios.get(`${API_BASE}/events/top-risks/${countryId}?limit=5`);
      setCountryEvents(eventRes.data || []);

      // Fetch local markets with country_code parameter
      const marketRes = await axios.get(`${API_BASE}/market/local/${countryId}?country_code=${countryCode}`);
      const data = marketRes.data;

      if (data && data.country_assets && data.country_assets.length > 0) {
        setIsFallback(false);
        setCountryMarkets(data.country_assets);
        setMarketContext({});
        handleSelectMarket(data.country_assets[0], countryCode);
      } else if (data && data.fallback_assets && data.fallback_assets.length > 0) {
        setIsFallback(true);
        setCountryMarkets(data.fallback_assets);
        setMarketContext(data.market_context || {});
        handleSelectMarket(data.fallback_assets[0], countryCode);
      } else {
        setIsFallback(false);
        setCountryMarkets([]);
        setMarketContext({});
        setSelectedMarket(null);
        setMarketHistory([]);
      }
    } catch (err) {
      console.error('Failed to load country details from backend:', err);
      setCountryEvents([]);
      setIsFallback(false);
      setCountryMarkets([]);
      setMarketContext({});
      setSelectedMarket(null);
      setMarketHistory([]);
    }
  };

  const handleSelectMarket = async (market: any, countryCodeOverride?: string) => {
    setSelectedMarket(market);
    setLoadingHistory(true);
    const code = countryCodeOverride || selectedCountry?.country_code || 'US';
    try {
      // Fetch market candlestick history with country_code parameter
      const historyRes = await axios.get(`${API_BASE}/market/${market.symbol}?country_code=${code}`);
      if (historyRes.data && historyRes.data.history && historyRes.data.history.length > 0) {
        setMarketHistory(historyRes.data.history);
      } else {
        setMarketHistory([]);
      }
    } catch (e) {
      console.error('Failed to load market history from backend:', e);
      setMarketHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  // 4. Style Leaflet country polygons
  const getStyleForFeature = (feature: any) => {
    const name = feature.properties.name;
    const iso2 = feature.properties.iso_a2;

    // O(1) lookup record to replace expensive O(N) array search on every render/hover
    const country = (iso2 && countryLookupMap[iso2.toUpperCase()]) ||
      (name && countryLookupMap[name.toLowerCase()]);

    const score = country?.risk_score ?? 20.0;
    const label = riskLabel(score);

    // Apply risk filtering
    const isFilteredOut = !selectedRiskFilters.includes(label);

    return {
      fillColor: isFilteredOut ? 'rgba(31, 35, 48, 0.4)' : riskColor(score),
      weight: 0.5,
      opacity: 0.7,
      color: 'rgba(255, 255, 255, 0.1)',
      fillOpacity: isFilteredOut ? 0.15 : 0.65,
    };
  };

  getStyleForFeatureRef.current = getStyleForFeature;

  // Polygon Hover / Click listeners
  const onEachFeature = (feature: any, layer: L.Layer) => {
    const name = feature.properties.name;
    const iso2 = feature.properties.iso_a2;

    // Bind initial tooltip with dynamic score initially set to 20.0 (will be updated dynamically)
    layer.bindTooltip(`<strong>${name}</strong><br/>Risk Score: 20.0`, {
      sticky: true,
      direction: 'top',
    });

    layer.on({
      mouseover: (e) => {
        const l = e.target as L.Path;
        l.setStyle({
          fillOpacity: 0.85,
          weight: 1.5,
        });
      },
      mouseout: (e) => {
        if (getStyleForFeatureRef.current) {
          e.target.setStyle(getStyleForFeatureRef.current(e.target.feature));
        }
      },
      click: () => {
        const latestCountries = countriesListRef.current;
        const country = latestCountries.find(
          (c) =>
            c.country_code.toUpperCase() === iso2?.toUpperCase() ||
            c.country_name.toLowerCase() === name?.toLowerCase()
        );
        if (country) {
          setSearchParams({ country: country.id.toString(), view: '2d' });
        } else {
          // If country risk not in database, create a temporary container
          const mockCountry = {
            id: 999,
            country_code: iso2 || 'XX',
            country_name: name,
            risk_score: 20.0,
          };
          setSelectedCountry(mockCountry);
          fetchCountryDetails(999, iso2 || 'XX');
        }
      },
    });
  };

  // Search fly-to capital execution
  const handleSearchSelect = (country: any) => {
    setSearchQuery('');
    setShowSearchResults(false);

    // Map capital coordinates for flying
    const coords = CAPITAL_COORDS[country.country_code];
    if (coords) {
      setFlyCentroid([coords.lat, coords.lon]);
    }
    setSearchParams({ country: country.id.toString(), view: '2d' });
  };

  // Toggle risk checkbox filter
  const handleToggleRiskFilter = (label: string) => {
    setSelectedRiskFilters((prev) =>
      prev.includes(label) ? prev.filter((r) => r !== label) : [...prev, label]
    );
  };

  // Force Leaflet layer color refresh and tooltip content update when variables change
  useEffect(() => {
    if (geoJsonLayerRef.current && geoJsonData) {
      geoJsonLayerRef.current.setStyle(getStyleForFeature);

      // Update tooltip content dynamically to avoid stale values using O(1) lookup
      geoJsonLayerRef.current.eachLayer((layer: any) => {
        const feature = layer.feature;
        if (feature) {
          const name = feature.properties.name;
          const iso2 = feature.properties.iso_a2;
          const country = (iso2 && countryLookupMap[iso2.toUpperCase()]) ||
            (name && countryLookupMap[name.toLowerCase()]);
          const score = country?.risk_score ?? 20.0;
          layer.setTooltipContent(`<strong>${name}</strong><br/>Risk Score: ${score.toFixed(1)}`);
        }
      });
    }
  }, [selectedRiskFilters, countryLookupMap]);

  // Search Results filtering
  const filteredCountries = countriesList.filter((c) =>
    c.country_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div
      style={{
        display: 'flex',
        height: 'calc(100vh - 104px)', // 56px Top nav + 48px Bottom status = 104px
        width: '100%',
        boxSizing: 'border-box',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* LEFT DRAWER PANEL: Filters */}
      <div
        style={{
          width: filterExpanded ? '220px' : '48px',
          flexShrink: 0,
          backgroundColor: 'var(--bg-surface)',
          borderRight: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          transition: 'width 300ms var(--ease-snap)',
          zIndex: 10,
          boxSizing: 'border-box',
          position: 'relative',
        }}
      >
        {filterExpanded ? (
          <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '20px', height: '100%', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '0.04em' }}>
                MAP CONTROLS
              </span>
              <button
                onClick={() => setFilterExpanded(false)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  padding: '4px',
                }}
              >
                <ChevronLeft size={16} />
              </button>
            </div>

            {/* Risk Filters */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)' }}>RISK FILTER</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {[
                  { label: 'CRITICAL', color: 'var(--risk-critical)' },
                  { label: 'HIGH', color: 'var(--accent-amber)' },
                  { label: 'MEDIUM', color: 'var(--accent-cyan)' },
                  { label: 'LOW', color: 'var(--risk-low)' },
                ].map((item) => {
                  const active = selectedRiskFilters.includes(item.label);
                  return (
                    <label
                      key={item.label}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '11px',
                        cursor: 'pointer',
                        color: active ? 'var(--text-primary)' : 'var(--text-muted)',
                        fontWeight: active ? 600 : 400,
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={active}
                        onChange={() => handleToggleRiskFilter(item.label)}
                        style={{ cursor: 'pointer' }}
                      />
                      <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: item.color }} />
                      {item.label}
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Active Hotspots / Themes */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)' }}>ACTIVE HOTSPOTS</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {['Taiwan Strait', 'Ukraine Border', 'Red Sea Corridor', 'Strait of Hormuz'].map((theme) => {
                  const isSelected = selectedThemes.includes(theme);
                  return (
                    <button
                      key={theme}
                      onClick={() => {
                        setSelectedThemes((p) =>
                          p.includes(theme) ? p.filter((t) => t !== theme) : [...p, theme]
                        );
                        // Trigger fly centroids for mock themes
                        if (theme === 'Taiwan Strait') setFlyCentroid([23.5, 121]);
                        if (theme === 'Ukraine Border') setFlyCentroid([49, 31]);
                        if (theme === 'Red Sea Corridor') setFlyCentroid([20, 40]);
                        if (theme === 'Strait of Hormuz') setFlyCentroid([26, 56]);
                      }}
                      style={{
                        textAlign: 'left',
                        padding: '6px 10px',
                        backgroundColor: isSelected ? 'rgba(6, 182, 212, 0.1)' : 'var(--bg-elevated)',
                        border: isSelected ? '1px solid var(--accent-cyan)' : '1px solid var(--border)',
                        borderRadius: 'var(--radius-sm)',
                        color: isSelected ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                        fontSize: '11px',
                        fontWeight: 600,
                        cursor: 'pointer',
                        transition: 'all 150ms ease',
                      }}
                    >
                      {theme}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: '16px' }}>
            <button
              onClick={() => setFilterExpanded(true)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                padding: '8px',
              }}
              title="Expand Controls"
            >
              <Filter size={18} />
            </button>
          </div>
        )}
      </div>

      {/* CENTER ZONE: Interactive Leaflet Map */}
      <div style={{ flex: 1, position: 'relative', height: '100%' }}>
        {/* Search-to-fly capital location input bar */}
        <div style={{ position: 'absolute', top: '16px', right: '16px', zIndex: 1000, width: '220px' }}>
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setShowSearchResults(true);
              }}
              onFocus={() => setShowSearchResults(true)}
              placeholder="Search countries..."
              style={{
                width: '100%',
                height: '34px',
                backgroundColor: 'rgba(26, 29, 36, 0.85)',
                border: '1px solid var(--border-bright)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-primary)',
                padding: '0 10px 0 32px',
                fontSize: '12px',
                backdropFilter: 'blur(8px)',
                boxSizing: 'border-box',
              }}
            />
            {showSearchResults && searchQuery && (
              <>
                <div onClick={() => setShowSearchResults(false)} style={{ position: 'fixed', inset: 0, zIndex: 999 }} />
                <div
                  style={{
                    position: 'absolute',
                    top: '38px',
                    left: 0,
                    right: 0,
                    backgroundColor: 'var(--bg-elevated)',
                    border: '1px solid var(--border-bright)',
                    borderRadius: 'var(--radius-md)',
                    maxHeight: '200px',
                    overflowY: 'auto',
                    zIndex: 1000,
                    padding: '4px',
                    boxShadow: 'var(--shadow)',
                  }}
                >
                  {filteredCountries.length === 0 ? (
                    <div style={{ padding: '8px', fontSize: '11px', color: 'var(--text-muted)' }}>No countries found</div>
                  ) : (
                    filteredCountries.map((c) => (
                      <div
                        key={c.country_code}
                        onClick={() => handleSearchSelect(c)}
                        style={{
                          padding: '6px 10px',
                          fontSize: '12px',
                          cursor: 'pointer',
                          borderRadius: 'var(--radius-sm)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-hover)')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                      >
                        <span>{c.country_name}</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: riskColor(c.risk_score), fontWeight: 700 }}>
                          {c.risk_score.toFixed(1)}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </>
            )}
          </div>
        </div>

        {/* 2D Leaflet World Map Container */}
        <MapContainer
          center={[20, 0]}
          zoom={2.5}
          minZoom={2}
          maxZoom={6}
          style={{ width: '100%', height: '100%', zIndex: 1 }}
          zoomControl={true}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution="© CartoDB"
          />
          {geoJsonData && (
            <GeoJSON
              ref={geoJsonLayerRef}
              data={geoJsonData}
              style={getStyleForFeature}
              onEachFeature={onEachFeature}
            />
          )}
          {/* Fly controller hooks */}
          <MapFlyController centroid={flyCentroid} />
        </MapContainer>
      </div>

      {/* RIGHT SLIDING PANEL: Country Details & Charts */}
      {selectedCountry && (
        <div
          style={{
            width: '500px',
            flexShrink: 0,
            backgroundColor: 'var(--bg-surface)',
            borderLeft: '1px solid var(--border)',
            boxShadow: 'var(--shadow)',
            zIndex: 11,
            display: 'flex',
            flexDirection: 'column',
            animation: 'slideIn 300ms var(--ease-snap)',
            boxSizing: 'border-box',
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: '16px',
              borderBottom: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '20px' }}>{getFlagEmoji(selectedCountry.country_code)}</span>
                <span style={{ fontSize: '15px', fontWeight: 700 }}>{selectedCountry.country_name}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', fontSize: '10px', color: 'var(--text-muted)' }}>
                <LiveDot />
                Live geopolitical feed
              </div>
            </div>

            <button
              onClick={() => {
                setSelectedCountry(null);
                setSearchParams({});
              }}
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

          {/* Details Scroll Area */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Risk details */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '12px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600 }}>OVERALL RISK</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '16px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: riskColor(selectedCountry.risk_score) }}>
                  {selectedCountry.risk_score.toFixed(1)}
                </span>
                <span style={{ fontSize: '10px', fontWeight: 700, color: riskColor(selectedCountry.risk_score), border: `1px solid ${riskColor(selectedCountry.risk_score)}`, padding: '2px 6px', borderRadius: 'var(--radius-sm)' }}>
                  {riskLabel(selectedCountry.risk_score)}
                </span>
              </div>
            </div>

            {/* Active country events */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.04em' }}>
                TOP COUNTRY EVENTS
              </span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {countryEvents.length === 0 ? (
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', padding: '8px 0' }}>
                    No recent high-severity events found.
                  </div>
                ) : (
                  countryEvents.map((e) => (
                    <div
                      key={e.id}
                      style={{
                        padding: '10px',
                        backgroundColor: 'var(--bg-elevated)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-md)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '6px' }}>
                        <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>{e.title}</span>
                        <SeverityBadge score={e.severity} showScore={false} />
                      </div>
                      <span style={{ display: 'block', fontSize: '9px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                        {formatRelativeTime(e.timestamp)}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Linked local assets */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.04em' }}>
                LINKED ASSETS
              </span>
              {countryMarkets.length === 0 ? (
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', padding: '8px 0' }}>
                  No registered assets linked to this country.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {/* Asset Tabs */}
                  <div style={{ display: 'flex', gap: '8px' }}>
                    {countryMarkets.map((m) => (
                      <button
                        key={m.symbol}
                        onClick={() => handleSelectMarket(m, selectedCountry?.country_code)}
                        style={{
                          flex: 1,
                          padding: '6px 12px',
                          backgroundColor: selectedMarket?.symbol === m.symbol ? 'var(--bg-elevated)' : 'transparent',
                          border: `1px solid ${selectedMarket?.symbol === m.symbol ? 'var(--border-bright)' : 'var(--border)'}`,
                          borderRadius: 'var(--radius-md)',
                          cursor: 'pointer',
                          color: selectedMarket?.symbol === m.symbol ? 'var(--text-primary)' : 'var(--text-secondary)',
                          fontSize: '11px',
                          fontWeight: 600,
                          textAlign: 'center',
                          transition: 'all 150ms ease',
                        }}
                      >
                        {m.symbol}
                      </button>
                    ))}
                  </div>

                  {/* Selected Asset details & Candlestick */}
                  {selectedMarket && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {isFallback && (
                        <div style={{
                          fontSize: '11px',
                          color: 'var(--accent-cyan)',
                          backgroundColor: 'rgba(6, 182, 212, 0.08)',
                          border: '1px solid rgba(6, 182, 212, 0.2)',
                          padding: '8px 12px',
                          borderRadius: 'var(--radius-md)',
                          marginBottom: '4px',
                          fontWeight: 500
                        }}>
                          ⚠️ No country-specific market asset available. Showing global market indicators.
                        </div>
                      )}

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <span style={{ fontSize: '13px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                            {selectedMarket.symbol}
                          </span>
                          <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                            {selectedMarket.name}
                          </span>
                        </div>
                        <span style={{ fontSize: '16px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                          {formatCurrency(selectedMarket.price, selectedMarket.currency_symbol || '$')}
                        </span>
                      </div>

                      {/* Candlestick Chart */}
                      {loadingHistory ? (
                        <div style={{ height: '180px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
                          <Loader2 size={16} className="animate-spin" />
                        </div>
                      ) : (
                        <CandlestickChart data={marketHistory} height={180} livePrice={selectedMarket?.price} />
                      )}

                      {/* Fallback description text */}
                      {isFallback && marketContext[selectedMarket.symbol] && (
                        <div style={{
                          fontSize: '11px',
                          color: 'var(--text-secondary)',
                          lineHeight: '1.4',
                          backgroundColor: 'rgba(255, 255, 255, 0.02)',
                          border: '1px solid var(--border)',
                          padding: '10px 12px',
                          borderRadius: 'var(--radius-md)',
                          fontStyle: 'italic'
                        }}>
                          {marketContext[selectedMarket.symbol]}
                        </div>
                      )}

                      <button
                        onClick={() => navigate(`/markets?asset=${selectedMarket.symbol}`)}
                        style={{
                          width: '100%',
                          height: '36px',
                          backgroundColor: 'transparent',
                          border: '1px solid var(--accent-cyan)',
                          color: 'var(--accent-cyan)',
                          fontSize: '11px',
                          fontWeight: 700,
                          borderRadius: 'var(--radius-sm)',
                          cursor: 'pointer',
                        }}
                      >
                        VIEW DEEP ALGORITHMIC SIGNAL
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
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

export default Map;
