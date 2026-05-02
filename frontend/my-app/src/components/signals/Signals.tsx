import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { signalsApi, forecastApi } from "../../api";
import { useUIStore } from "../../store";
import {
  TrendingUp, TrendingDown, Minus, Filter, Zap,
  Target, Brain, BarChart2, Shield, ChevronDown
} from "lucide-react";

// ── Helpers ────────────────────────────────────────────────────────────────────

const sigColor = (t?: string) =>
  t === "BUY" ? "var(--buy)" : t === "SELL" ? "var(--sell)" : "var(--hold)";

const sigBg = (t?: string) =>
  t === "BUY" ? "var(--buy-dim)" : t === "SELL" ? "var(--sell-dim)" : "var(--hold-dim)";

const sigBorder = (t?: string) =>
  t === "BUY" ? "var(--buy-border)" : t === "SELL" ? "var(--sell-border)" : "var(--hold-border)";

const SigIcon = ({ type }: { type?: string }) => {
  if (type === "BUY")  return <TrendingUp  size={14} style={{ color: "var(--buy)" }} />;
  if (type === "SELL") return <TrendingDown size={14} style={{ color: "var(--sell)" }} />;
  return <Minus size={14} style={{ color: "var(--hold)" }} />;
};

const ASSET_CLASSES = ["All", "Stocks", "ETFs", "Forex", "Crypto", "Commodities", "Bonds", "Indices"];
const DIRECTIONS = ["All", "BUY", "SELL", "HOLD"];

const DETAIL_TABS = [
  { id: "trade",     label: "Trade Setup",    icon: Target    },
  { id: "reasoning", label: "AI Reasoning",   icon: Brain     },
  { id: "forecast",  label: "MC Forecast",    icon: BarChart2 },
  { id: "reliability", label: "Reliability",  icon: Shield    },
];

const MetricRow = ({ label, value, unit = "" }: { label: string; value?: number | string; unit?: string }) => (
  <div className="flex items-center justify-between py-2"
    style={{ borderBottom: "1px solid var(--border-subtle)" }}>
    <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "10px", color: "var(--text-muted)", letterSpacing: "0.04em" }}>
      {label}
    </span>
    <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", color: "var(--text-primary)", fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
      {value !== undefined && value !== null ? `${value}${unit}` : "—"}
    </span>
  </div>
);

const BarFill = ({ value, color = "var(--amber)" }: { value?: number; color?: string }) => (
  <div className="strength-bar flex-1">
    <div className="strength-bar-fill-amber" style={{
      width: `${Math.round((value || 0) * 100)}%`,
      background: color,
    }} />
  </div>
);

// ── Main ───────────────────────────────────────────────────────────────────────

export default function Signals() {
  const { filters, setFilters } = useUIStore();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detailTab, setDetailTab] = useState("trade");
  const [showFilters, setShowFilters] = useState(true);

  const assetClass = filters.signalAssetClass || "All";
  const direction  = filters.signalDirection  || "All";

  // Fetch signals with market context
  const { data: signalsData, isLoading } = useQuery({
    queryKey: ["signals-with-market-full"],
    queryFn: () => signalsApi.getWithMarket(0, 100),
    refetchInterval: 60000,
  });

  // Fetch single signal detail
  const { data: detailData } = useQuery({
    queryKey: ["signal-detail", selectedId],
    queryFn: () => signalsApi.getSignal(selectedId!),
    enabled: !!selectedId,
  });

  const allSignals: any[] = signalsData?.data || [];
  const detail = detailData?.data;

  // Filter signals
  const filtered = allSignals.filter((s) => {
    const classMatch = assetClass === "All" || s.market_asset_class === assetClass;
    const dirMatch   = direction  === "All" || s.signal_type === direction;
    return classMatch && dirMatch;
  });

  // Auto-select first signal when the list loads
  useEffect(() => {
    if (filtered.length > 0 && !selectedId) {
      setSelectedId(filtered[0].id);
    }
  }, [filtered, selectedId]);

  // Selected signal (use list data for fast display before detail loads)
  const selected = detail || allSignals.find((s) => s.id === selectedId);

  // MC Forecast for selected asset
  const { data: mcData } = useQuery({
    queryKey: ["mc-signals", selected?.market_id],
    queryFn: () => forecastApi.getMonteCarloForecast(selected!.market_id, 30, 5000),
    enabled: !!selected?.market_id && detailTab === "forecast",
  });
  const mc = mcData?.data;

  return (
    <div className="flex h-full overflow-hidden select-none"
      style={{ backgroundColor: "var(--bg-primary)" }}>

      {/* ── LEFT: Filter + Signal List ─────────────────────────────────── */}
      <motion.div
        initial={{ x: -30, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="flex flex-col border-r shrink-0"
        style={{ width: 300, borderColor: "var(--border)", backgroundColor: "var(--bg-secondary)" }}
      >
        {/* Filter bar */}
        <div className="px-4 py-3 border-b shrink-0" style={{ borderColor: "var(--border)" }}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Zap size={12} style={{ color: "var(--amber)" }} />
              <span className="section-label" style={{ color: "var(--amber)" }}>
                AI SIGNALS · {filtered.length}
              </span>
            </div>
            <button
              onClick={() => setShowFilters(f => !f)}
              className="flex items-center gap-1 cursor-pointer transition-all"
              style={{ fontFamily: "'Space Mono', monospace", fontSize: "9px", color: "var(--text-muted)" }}
            >
              <Filter size={10} />
              {showFilters ? "HIDE" : "FILTER"}
              <ChevronDown size={9} style={{ transform: showFilters ? "rotate(180deg)" : "none", transition: "transform 0.15s" }} />
            </button>
          </div>

          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden space-y-2"
              >
                {/* Asset class filter */}
                <div>
                  <span className="section-label" style={{ fontSize: "8px", color: "var(--text-ghost)" }}>ASSET CLASS</span>
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {ASSET_CLASSES.map((c) => (
                      <button
                        key={c}
                        onClick={() => setFilters({ signalAssetClass: c })}
                        className="px-2 py-0.5 cursor-pointer transition-all"
                        style={{
                          fontFamily: "'Space Mono', monospace",
                          fontSize: "8px",
                          fontWeight: 700,
                          letterSpacing: "0.05em",
                          borderRadius: 1,
                          border: `1px solid ${assetClass === c ? "var(--amber-border)" : "var(--border-subtle)"}`,
                          background: assetClass === c ? "var(--amber-glow)" : "transparent",
                          color: assetClass === c ? "var(--amber)" : "var(--text-muted)",
                        }}
                      >
                        {c.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>
                {/* Direction filter */}
                <div>
                  <span className="section-label" style={{ fontSize: "8px", color: "var(--text-ghost)" }}>DIRECTION</span>
                  <div className="flex gap-1 mt-1.5">
                    {DIRECTIONS.map((d) => (
                      <button
                        key={d}
                        onClick={() => setFilters({ signalDirection: d })}
                        className="px-2 py-0.5 cursor-pointer transition-all"
                        style={{
                          fontFamily: "'Space Mono', monospace",
                          fontSize: "8px",
                          fontWeight: 700,
                          borderRadius: 1,
                          border: `1px solid ${direction === d ? sigBorder(d) : "var(--border-subtle)"}`,
                          background: direction === d ? sigBg(d) : "transparent",
                          color: direction === d ? sigColor(d) : "var(--text-muted)",
                        }}
                      >
                        {d}
                      </button>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Signal list */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin"
                style={{ borderColor: "var(--amber-border)", borderTopColor: "transparent" }} />
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 gap-2">
              <Zap size={20} style={{ color: "var(--text-ghost)" }} />
              <span className="section-label">NO SIGNALS</span>
            </div>
          ) : (
            filtered.map((s: any, i: number) => {
              const active = s.id === selectedId;
              return (
                <motion.div
                  key={s.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.025 }}
                  onClick={() => setSelectedId(s.id)}
                  className="flex items-center justify-between px-4 py-3 cursor-pointer group transition-all"
                  style={{
                    backgroundColor: active ? "var(--amber-glow)" : "transparent",
                    borderLeft: active ? "2px solid var(--amber)" : "2px solid transparent",
                    borderBottom: "1px solid var(--border-subtle)",
                  }}
                  onMouseEnter={e => {
                    if (!active) (e.currentTarget as HTMLElement).style.backgroundColor = "var(--bg-hover)";
                  }}
                  onMouseLeave={e => {
                    if (!active) (e.currentTarget as HTMLElement).style.backgroundColor = "transparent";
                  }}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <SigIcon type={s.signal_type} />
                    <div className="min-w-0">
                      <div style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", fontWeight: 700, color: "var(--text-primary)" }}>
                        {s.market_symbol}
                      </div>
                      <div className="truncate" style={{ fontFamily: "Inter, sans-serif", fontSize: "9px", color: "var(--text-muted)", maxWidth: 120 }}>
                        {s.market_name || s.market_asset_class || "—"}
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <span style={{
                      fontFamily: "'Space Mono', monospace",
                      fontSize: "9px",
                      fontWeight: 700,
                      color: sigColor(s.signal_type),
                      background: sigBg(s.signal_type),
                      border: `1px solid ${sigBorder(s.signal_type)}`,
                      padding: "1px 5px",
                      borderRadius: 1,
                    }}>
                      {s.signal_type}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <div className="strength-bar w-16">
                        <div style={{
                          height: "100%",
                          width: `${Math.round((s.confidence || 0) * 100)}%`,
                          background: sigColor(s.signal_type),
                          transition: "width 0.5s ease",
                        }} />
                      </div>
                      <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "8px", color: "var(--text-muted)", fontVariantNumeric: "tabular-nums" }}>
                        {s.confidence != null ? `${(s.confidence * 100).toFixed(0)}%` : "—"}
                      </span>
                    </div>
                  </div>
                </motion.div>
              );
            })
          )}
        </div>
      </motion.div>

      {/* ── RIGHT: Signal Detail ───────────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {!selectedId ? (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <Zap size={32} style={{ color: "var(--text-ghost)" }} />
            <span style={{ fontFamily: "'Syne', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--text-muted)" }}>
              Select a signal to inspect
            </span>
            <p className="section-label">Click any signal in the list to view full intelligence report</p>
          </div>
        ) : selected ? (
          <motion.div
            key={selected.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.25 }}
            className="flex flex-col h-full overflow-hidden"
          >
            {/* Signal header */}
            <div className="px-6 py-4 border-b shrink-0"
              style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-secondary)" }}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <SigIcon type={selected.signal_type} />
                    <span style={{
                      fontFamily: "'Syne', sans-serif",
                      fontSize: "22px",
                      fontWeight: 800,
                      color: "var(--text-primary)",
                      letterSpacing: "-0.02em",
                    }}>
                      {selected.market_symbol}
                    </span>
                    {selected.market_name && (
                      <span style={{ fontFamily: "Inter, sans-serif", fontSize: "12px", color: "var(--text-muted)" }}>
                        {selected.market_name}
                      </span>
                    )}
                    <span style={{
                      fontFamily: "'Space Mono', monospace",
                      fontSize: "11px",
                      fontWeight: 700,
                      color: sigColor(selected.signal_type),
                      background: sigBg(selected.signal_type),
                      border: `1px solid ${sigBorder(selected.signal_type)}`,
                      padding: "3px 10px",
                      borderRadius: 1,
                    }}>
                      {selected.signal_type}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 flex-wrap">
                    {selected.market_asset_class && (
                      <span className="section-label">
                        {selected.market_asset_class}
                      </span>
                    )}
                    {selected.confidence != null && (
                      <div className="flex items-center gap-2">
                        <span className="section-label">CONFIDENCE</span>
                        <div className="flex items-center gap-2">
                          <div className="strength-bar w-24">
                            <div style={{
                              height: "100%",
                              width: `${Math.round(selected.confidence * 100)}%`,
                              background: sigColor(selected.signal_type),
                            }} />
                          </div>
                          <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "12px", fontWeight: 700, color: sigColor(selected.signal_type) }}>
                            {(selected.confidence * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    )}
                    {selected.triggering_event && (
                      <span className="section-label px-2 py-0.5"
                        style={{ background: "var(--sell-dim)", color: "var(--sell)", borderRadius: 1 }}>
                        ⚡ {selected.triggering_event}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  {selected.market_price != null && (
                    <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "18px", fontWeight: 700, color: "var(--text-primary)" }}>
                      {selected.market_price?.toLocaleString("en-US", { maximumFractionDigits: 4 })}
                    </span>
                  )}
                  {selected.market_geo_sensitivity != null && (
                    <div className="flex items-center gap-2">
                      <span className="section-label">GEO SENSITIVITY</span>
                      <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", color: "var(--amber)" }}>
                        {(selected.market_geo_sensitivity * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Tags */}
              {selected.tags?.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {selected.tags.map((tag: string) => (
                    <span key={tag} style={{
                      fontFamily: "'Space Mono', monospace",
                      fontSize: "8px",
                      fontWeight: 700,
                      letterSpacing: "0.05em",
                      padding: "2px 7px",
                      borderRadius: 1,
                      background: "var(--violet-dim)",
                      border: "1px solid var(--violet-border)",
                      color: "var(--violet)",
                    }}>
                      {tag.toUpperCase()}
                    </span>
                  ))}
                </div>
              )}

              {/* Detail Tab Nav */}
              <div className="flex gap-0 mt-4 border-b -mb-4" style={{ borderColor: "var(--border)" }}>
                {DETAIL_TABS.map((t) => {
                  const Icon = t.icon;
                  const active = detailTab === t.id;
                  return (
                    <button
                      key={t.id}
                      onClick={() => setDetailTab(t.id)}
                      className="flex items-center gap-1.5 px-4 py-2 cursor-pointer transition-all"
                      style={{
                        fontFamily: "'Space Mono', monospace",
                        fontSize: "9px",
                        fontWeight: 700,
                        letterSpacing: "0.08em",
                        textTransform: "uppercase",
                        color: active ? "var(--amber)" : "var(--text-muted)",
                        borderBottom: active ? "2px solid var(--amber)" : "2px solid transparent",
                        backgroundColor: "transparent",
                        border: "none",
                        cursor: "pointer",
                        paddingBottom: "10px",
                      }}
                    >
                      <Icon size={10} />
                      {t.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Tab content */}
            <div className="flex-1 overflow-y-auto px-6 py-5">
              <AnimatePresence mode="wait">
                <motion.div
                  key={detailTab}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.18 }}
                >
                  {detailTab === "trade" && (
                    <div className="grid grid-cols-2 gap-6">
                      {/* Trade parameters */}
                      <div className="war-card p-5">
                        <span className="section-label mb-3 block">TRADE PARAMETERS</span>
                        <MetricRow label="SIGNAL TYPE"    value={selected.signal_type} />
                        <MetricRow label="CONFIDENCE"     value={selected.confidence != null ? `${(selected.confidence * 100).toFixed(1)}%` : undefined} />
                        <MetricRow label="STOP LOSS"      value={selected.stop_loss?.toLocaleString("en-US", { maximumFractionDigits: 4 })} />
                        <MetricRow label="TARGET PRICE"   value={selected.target_price?.toLocaleString("en-US", { maximumFractionDigits: 4 })} />
                        <MetricRow label="VOLATILITY LVL" value={selected.volatility_level} />
                        <MetricRow label="HORIZON"        value={selected.time_horizon} />
                        <MetricRow label="RISK/REWARD"    value={
                          selected.target_price && selected.stop_loss && selected.market_price
                            ? ((selected.target_price - selected.market_price) /
                               (selected.market_price - selected.stop_loss)).toFixed(2)
                            : undefined
                        } />
                      </div>

                      {/* Risk Factors */}
                      <div className="war-card p-5">
                        <span className="section-label mb-3 block">RISK FACTORS</span>
                        {selected.risk_factors?.length > 0 ? (
                          <div className="space-y-2">
                            {selected.risk_factors.map((rf: string, i: number) => (
                              <motion.div
                                key={i}
                                initial={{ opacity: 0, x: 8 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: i * 0.04 }}
                                className="flex items-start gap-2 py-1.5"
                                style={{ borderBottom: "1px solid var(--border-subtle)" }}
                              >
                                <span style={{ color: "var(--sell)", marginTop: 1 }}>▸</span>
                                <span style={{ fontFamily: "Inter, sans-serif", fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                                  {rf}
                                </span>
                              </motion.div>
                            ))}
                          </div>
                        ) : (
                          <p className="section-label">NO RISK FACTORS</p>
                        )}
                      </div>

                      {/* Signal Source */}
                      <div className="war-card p-5 col-span-2">
                        <span className="section-label mb-3 block">SIGNAL INTELLIGENCE SOURCE</span>
                        <div className="grid grid-cols-3 gap-4">
                          <MetricRow label="AI SOURCE"  value={selected.ai_source} />
                          <MetricRow label="DRIFT"      value={selected.predicted_drift != null ? `${(selected.predicted_drift * 100).toFixed(2)}%` : undefined} />
                          <MetricRow label="VOLATILITY" value={selected.predicted_volatility != null ? `${(selected.predicted_volatility * 100).toFixed(2)}%` : undefined} />
                        </div>
                      </div>
                    </div>
                  )}

                  {detailTab === "reasoning" && (
                    <div className="space-y-4 max-w-3xl">
                      <div className="war-card p-5">
                        <span className="section-label mb-3 block" style={{ color: "var(--violet)" }}>AI REASONING</span>
                        <p style={{ fontFamily: "Inter, sans-serif", fontSize: "13px", lineHeight: 1.75, color: "var(--text-secondary)" }}>
                          {selected.reasoning || "No reasoning available for this signal."}
                        </p>
                      </div>
                      {selected.triggering_event && (
                        <div className="war-card p-5">
                          <span className="section-label mb-2 block">TRIGGERING EVENT</span>
                          <p style={{ fontFamily: "Inter, sans-serif", fontSize: "12px", color: "var(--sell)" }}>
                            ⚡ {selected.triggering_event}
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {detailTab === "forecast" && (
                    <div className="space-y-4">
                      {mc ? (
                        <>
                          <div className="grid grid-cols-4 gap-4">
                            {[
                              { label: "VaR 95%",     value: mc.risk_metrics?.var_95, unit: "%" },
                              { label: "CVaR 95%",    value: mc.risk_metrics?.cvar_95, unit: "%" },
                              { label: "Sharpe",      value: mc.risk_metrics?.sharpe_ratio },
                              { label: "P(Loss)",     value: mc.risk_metrics?.probability_of_loss, unit: "%" },
                            ].map(({ label, value, unit = "" }) => (
                              <div key={label} className="war-card p-4 flex flex-col items-center gap-1">
                                <span className="section-label">{label}</span>
                                <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "18px", fontWeight: 800, color: "var(--amber)", letterSpacing: "-0.02em" }}>
                                  {value != null ? `${typeof value === "number" ? value.toFixed(2) : value}${unit}` : "—"}
                                </span>
                              </div>
                            ))}
                          </div>
                          <div className="war-card p-5">
                            <span className="section-label mb-3 block">30-DAY PRICE CONE (GBM · 5,000 PATHS)</span>
                            <div className="grid grid-cols-3 gap-4">
                              <MetricRow label="MEDIAN PATH"  value={mc.percentile_paths?.median?.slice(-1)[0]?.toFixed(2)} />
                              <MetricRow label="UPPER 95%"    value={mc.percentile_paths?.upper_95?.slice(-1)[0]?.toFixed(2)} />
                              <MetricRow label="LOWER 5%"     value={mc.percentile_paths?.lower_05?.slice(-1)[0]?.toFixed(2)} />
                              <MetricRow label="DRIFT (μ)"    value={mc.drift != null ? `${(mc.drift * 100).toFixed(2)}%` : undefined} />
                              <MetricRow label="VOLATILITY (σ)" value={mc.volatility != null ? `${(mc.volatility * 100).toFixed(2)}%` : undefined} />
                              <MetricRow label="GTI ADJUSTED" value={mc.gti_adjusted ? "YES" : "NO"} />
                            </div>
                          </div>
                        </>
                      ) : (
                        <div className="flex flex-col items-center justify-center h-48 gap-3">
                          <div className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin"
                            style={{ borderColor: "var(--amber-border)", borderTopColor: "transparent" }} />
                          <span className="section-label">COMPUTING 5,000 SIMULATION PATHS...</span>
                        </div>
                      )}
                    </div>
                  )}

                  {detailTab === "reliability" && (
                    <div className="grid grid-cols-2 gap-6">
                      <div className="war-card p-5">
                        <span className="section-label mb-4 block" style={{ color: "var(--amber)" }}>BACKTESTED METRICS</span>
                        <div className="space-y-4">
                          {[
                            { label: "Signal Accuracy",    value: selected.signal_accuracy,          color: "var(--buy)" },
                            { label: "Win Rate",           value: selected.win_rate,                  color: "var(--buy)" },
                            { label: "Annual Reliability", value: selected.annual_reliability_score,  color: "var(--amber)" },
                            { label: "Max Drawdown",       value: selected.max_drawdown,              color: "var(--sell)" },
                          ].map(({ label, value, color }) => (
                            <div key={label}>
                              <div className="flex items-center justify-between mb-1.5">
                                <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "10px", color: "var(--text-muted)", letterSpacing: "0.04em" }}>
                                  {label.toUpperCase()}
                                </span>
                                <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", fontWeight: 700, color }}>
                                  {value != null ? `${(value * 100).toFixed(1)}%` : "N/A"}
                                </span>
                              </div>
                              <BarFill value={value} color={color} />
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="war-card p-5">
                        <span className="section-label mb-4 block" style={{ color: "var(--amber)" }}>RISK-ADJUSTED STATS</span>
                        <MetricRow label="SHARPE RATIO"    value={selected.sharpe_ratio?.toFixed(3)} />
                        <MetricRow label="AI SOURCE"       value={selected.ai_source} />
                        <MetricRow label="SIGNAL CLASS"    value={selected.market_asset_class} />
                        <MetricRow label="GEO SENSITIVITY" value={selected.market_geo_sensitivity != null ? `${(selected.market_geo_sensitivity * 100).toFixed(0)}%` : undefined} />
                        <MetricRow label="SIGNAL AGE"      value={selected.created_at ? new Date(selected.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "2-digit" }) : undefined} />
                      </div>
                    </div>
                  )}
                </motion.div>
              </AnimatePresence>
            </div>
          </motion.div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: "var(--amber-border)", borderTopColor: "transparent" }} />
          </div>
        )}
      </div>
    </div>
  );
}
