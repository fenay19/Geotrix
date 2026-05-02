import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { marketApi, forecastApi, signalsApi } from "../../api";
import { TrendingUp, TrendingDown, Minus, Search, BarChart2, X } from "lucide-react";

const CLASSES = ["All", "Stocks", "ETFs", "Forex", "Crypto", "Commodities", "Bonds", "Indices"];

const sigColor = (t?: string) =>
  t === "BUY" ? "var(--buy)" : t === "SELL" ? "var(--sell)" : "var(--hold)";
const sigBg = (t?: string) =>
  t === "BUY" ? "var(--buy-dim)" : t === "SELL" ? "var(--sell-dim)" : "var(--hold-dim)";

const geoBar = (v: number) => {
  const color = v > 0.8 ? "var(--sell)" : v > 0.5 ? "var(--hold)" : "var(--buy)";
  return (
    <div className="flex items-center gap-2">
      <div className="strength-bar" style={{ width: 56 }}>
        <div style={{ height: "100%", width: `${v * 100}%`, background: color, transition: "width 0.4s ease" }} />
      </div>
      <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "9px", color, fontVariantNumeric: "tabular-nums" }}>
        {Math.round(v * 100)}%
      </span>
    </div>
  );
};

const fmtPrice = (p?: number) => {
  if (!p && p !== 0) return "—";
  if (p >= 10000) return p.toLocaleString("en-US", { maximumFractionDigits: 0 });
  if (p >= 100)   return p.toLocaleString("en-US", { maximumFractionDigits: 2 });
  return p.toFixed(4);
};

export default function Markets() {
  const [activeClass, setActiveClass] = useState("All");
  const [search, setSearch] = useState("");
  const [selectedMarket, setSelectedMarket] = useState<any>(null);

  const { data: marketsData, isLoading } = useQuery({
    queryKey: ["markets-all-signals"],
    queryFn: () => marketApi.getAllWithSignals(),
    refetchInterval: 30000,
  });

  // MC for selected market
  const { data: mcData } = useQuery({
    queryKey: ["mc-market", selectedMarket?.id],
    queryFn: () => forecastApi.getMonteCarloForecast(selectedMarket!.id, 30, 3000),
    enabled: !!selectedMarket?.id,
  });

  // Latest signal for selected market
  const { data: sigData } = useQuery({
    queryKey: ["signal-market", selectedMarket?.id],
    queryFn: () => signalsApi.getLatestSignal(selectedMarket!.id),
    enabled: !!selectedMarket?.id,
  });

  const allMarkets: any[] = marketsData?.data || [];

  const filtered = allMarkets.filter((m: any) => {
    const classOk = activeClass === "All" || m.asset_class === activeClass;
    const searchOk = !search || m.symbol.toLowerCase().includes(search.toLowerCase())
      || m.name?.toLowerCase().includes(search.toLowerCase());
    return classOk && searchOk;
  });

  const mc = mcData?.data;
  const sig = sigData?.data;

  return (
    <div className="flex h-full overflow-hidden select-none"
      style={{ backgroundColor: "var(--bg-primary)" }}>

      {/* ── Main Content ────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Header bar */}
        <motion.div
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="flex items-center justify-between px-6 py-3 border-b shrink-0"
          style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-secondary)" }}
        >
          <div className="flex items-center gap-4">
            <BarChart2 size={14} style={{ color: "var(--amber)" }} />
            <span className="section-label" style={{ color: "var(--amber)" }}>
              MARKETS · {filtered.length} ASSETS
            </span>
          </div>
          {/* Search */}
          <div className="flex items-center gap-2 px-3 py-1.5"
            style={{ background: "var(--bg-void)", border: "1px solid var(--border)", borderRadius: 1, minWidth: 200 }}>
            <Search size={11} style={{ color: "var(--text-muted)" }} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search symbol or name..."
              style={{
                background: "transparent",
                border: "none",
                outline: "none",
                fontFamily: "'Space Mono', monospace",
                fontSize: "11px",
                color: "var(--text-primary)",
                width: 160,
              }}
            />
          </div>
        </motion.div>

        {/* Asset class tabs */}
        <div className="flex items-center gap-1 px-6 py-3 border-b overflow-x-auto shrink-0"
          style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-secondary)" }}>
          {CLASSES.map((c) => (
            <motion.button
              key={c}
              whileTap={{ scale: 0.93 }}
              onClick={() => setActiveClass(c)}
              className="px-3 py-1 cursor-pointer transition-all whitespace-nowrap shrink-0"
              style={{
                fontFamily: "'Space Mono', monospace",
                fontSize: "9px",
                fontWeight: 700,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                borderRadius: 1,
                border: `1px solid ${activeClass === c ? "var(--amber-border)" : "var(--border-subtle)"}`,
                background: activeClass === c ? "var(--amber-glow)" : "transparent",
                color: activeClass === c ? "var(--amber)" : "var(--text-muted)",
              }}
            >
              {c}
            </motion.button>
          ))}
        </div>

        {/* Card Grid */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {isLoading ? (
            <div className="flex items-center justify-center h-48">
              <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin"
                style={{ borderColor: "var(--amber-border)", borderTopColor: "transparent" }} />
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 gap-3">
              <BarChart2 size={24} style={{ color: "var(--text-ghost)" }} />
              <span className="section-label">NO ASSETS FOUND</span>
            </div>
          ) : (
            <motion.div
              layout
              className="grid gap-3"
              style={{ gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))" }}
            >
              <AnimatePresence>
                {filtered.map((m: any, i: number) => {
                  const SigIco = m.latest_signal_type === "BUY" ? TrendingUp
                    : m.latest_signal_type === "SELL" ? TrendingDown : Minus;
                  return (
                    <motion.div
                      key={m.id}
                      layout
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ delay: Math.min(i * 0.02, 0.3), duration: 0.2 }}
                      onClick={() => setSelectedMarket(m)}
                      className="war-card p-4 cursor-pointer transition-all"
                      style={{ transition: "border-color 0.15s, box-shadow 0.15s" }}
                      onMouseEnter={e => {
                        (e.currentTarget as HTMLElement).style.borderColor = "var(--amber-border)";
                        (e.currentTarget as HTMLElement).style.boxShadow = "0 0 12px var(--amber-glow)";
                      }}
                      onMouseLeave={e => {
                        (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                        (e.currentTarget as HTMLElement).style.boxShadow = "none";
                      }}
                    >
                      {/* Card header */}
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <div style={{ fontFamily: "'Space Mono', monospace", fontSize: "12px", fontWeight: 700, color: "var(--text-primary)" }}>
                            {m.symbol}
                          </div>
                          <div className="truncate" style={{ fontFamily: "Inter, sans-serif", fontSize: "10px", color: "var(--text-muted)", maxWidth: 120 }}>
                            {m.name}
                          </div>
                        </div>
                        {m.latest_signal_type && (
                          <SigIco size={16} style={{ color: sigColor(m.latest_signal_type) }} />
                        )}
                      </div>

                      {/* Price */}
                      <div style={{ fontFamily: "'Space Mono', monospace", fontSize: "16px", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em", fontVariantNumeric: "tabular-nums", marginBottom: 8 }}>
                        {fmtPrice(m.price)}
                      </div>

                      {/* Signal badge */}
                      {m.latest_signal_type && (
                        <div className="flex items-center justify-between mb-2">
                          <span style={{
                            fontFamily: "'Space Mono', monospace",
                            fontSize: "9px",
                            fontWeight: 700,
                            letterSpacing: "0.05em",
                            padding: "2px 7px",
                            borderRadius: 1,
                            background: sigBg(m.latest_signal_type),
                            border: `1px solid ${sigColor(m.latest_signal_type)}33`,
                            color: sigColor(m.latest_signal_type),
                          }}>
                            {m.latest_signal_type}
                          </span>
                          <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "9px", color: "var(--text-muted)" }}>
                            {m.latest_signal_confidence != null ? `${(m.latest_signal_confidence * 100).toFixed(0)}%` : ""}
                          </span>
                        </div>
                      )}

                      {/* Geo sensitivity */}
                      {m.geo_sensitivity != null && (
                        <div>
                          <span className="section-label" style={{ fontSize: "7px" }}>GEO SENSITIVITY</span>
                          <div className="mt-1">{geoBar(m.geo_sensitivity)}</div>
                        </div>
                      )}

                      {/* Asset class badge */}
                      <div className="mt-2">
                        <span className="section-label" style={{
                          background: "var(--bg-void)",
                          padding: "2px 6px",
                          borderRadius: 1,
                          border: "1px solid var(--border-subtle)",
                        }}>
                          {m.asset_class}
                        </span>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </motion.div>
          )}
        </div>
      </div>

      {/* ── Asset Detail Panel ──────────────────────────────────────────── */}
      <AnimatePresence>
        {selectedMarket && (
          <motion.div
            initial={{ x: 320, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 320, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col border-l overflow-hidden shrink-0"
            style={{ width: 360, borderColor: "var(--border)", backgroundColor: "var(--bg-secondary)" }}
          >
            {/* Detail header */}
            <div className="flex items-center justify-between px-5 py-4 border-b shrink-0"
              style={{ borderColor: "var(--border)" }}>
              <div>
                <div style={{ fontFamily: "'Syne', sans-serif", fontSize: "18px", fontWeight: 800, color: "var(--text-primary)" }}>
                  {selectedMarket.symbol}
                </div>
                <div style={{ fontFamily: "Inter, sans-serif", fontSize: "11px", color: "var(--text-muted)" }}>
                  {selectedMarket.name}
                </div>
              </div>
              <button onClick={() => setSelectedMarket(null)}
                className="p-1.5 rounded cursor-pointer transition-all"
                style={{ border: "1px solid var(--border)", color: "var(--text-muted)" }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = "var(--text-primary)"}
                onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = "var(--text-muted)"}
              >
                <X size={13} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              {/* Price + signal */}
              <div className="war-card p-4">
                <div className="flex items-center justify-between mb-3">
                  <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "22px", fontWeight: 800, color: "var(--text-primary)", fontVariantNumeric: "tabular-nums" }}>
                    {fmtPrice(selectedMarket.price)}
                  </span>
                  {selectedMarket.latest_signal_type && (
                    <span style={{
                      fontFamily: "'Space Mono', monospace",
                      fontSize: "11px",
                      fontWeight: 700,
                      padding: "3px 10px",
                      borderRadius: 1,
                      background: sigBg(selectedMarket.latest_signal_type),
                      border: `1px solid ${sigColor(selectedMarket.latest_signal_type)}44`,
                      color: sigColor(selectedMarket.latest_signal_type),
                    }}>
                      {selectedMarket.latest_signal_type} · {selectedMarket.latest_signal_confidence != null ? `${(selectedMarket.latest_signal_confidence * 100).toFixed(0)}%` : ""}
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span className="section-label" style={{ fontSize: "7px" }}>ASSET CLASS</span>
                    <div style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", color: "var(--amber)", fontWeight: 700 }}>
                      {selectedMarket.asset_class}
                    </div>
                  </div>
                  <div>
                    <span className="section-label" style={{ fontSize: "7px" }}>GEO SENSITIVITY</span>
                    <div className="mt-1">{selectedMarket.geo_sensitivity != null ? geoBar(selectedMarket.geo_sensitivity) : <span className="section-label">—</span>}</div>
                  </div>
                </div>
              </div>

              {/* Latest signal detail */}
              {sig && (
                <div className="war-card p-4">
                  <span className="section-label mb-3 block" style={{ color: "var(--violet)" }}>LATEST AI SIGNAL</span>
                  <div style={{ fontFamily: "'Space Mono', monospace", fontSize: "10px", color: "var(--text-muted)", lineHeight: 1.8, letterSpacing: "0.02em" }}>
                    {[
                      { k: "STOP LOSS", v: sig.stop_loss?.toFixed(2) },
                      { k: "TARGET",    v: sig.target_price?.toFixed(2) },
                      { k: "HORIZON",   v: sig.time_horizon },
                      { k: "DRIFT",     v: sig.predicted_drift != null ? `${(sig.predicted_drift * 100).toFixed(2)}%` : null },
                      { k: "VOLATILITY", v: sig.predicted_volatility != null ? `${(sig.predicted_volatility * 100).toFixed(2)}%` : null },
                    ].map(({ k, v }) => v ? (
                      <div key={k} className="flex justify-between py-1" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                        <span style={{ color: "var(--text-muted)" }}>{k}</span>
                        <span style={{ color: "var(--text-primary)", fontWeight: 700 }}>{v}</span>
                      </div>
                    ) : null)}
                  </div>
                  {sig.reasoning && (
                    <p className="mt-3" style={{ fontFamily: "Inter, sans-serif", fontSize: "11px", lineHeight: 1.65, color: "var(--text-secondary)" }}>
                      {sig.reasoning.slice(0, 240)}{sig.reasoning.length > 240 ? "..." : ""}
                    </p>
                  )}
                </div>
              )}

              {/* Monte Carlo Risk Metrics */}
              {mc?.risk_metrics && (
                <div className="war-card p-4">
                  <span className="section-label mb-3 block" style={{ color: "var(--amber)" }}>30-DAY MC FORECAST</span>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { label: "VaR 95%",  value: mc.risk_metrics.var_95,                 color: "var(--sell)" },
                      { label: "CVaR 95%", value: mc.risk_metrics.cvar_95,                color: "var(--sell)" },
                      { label: "Sharpe",   value: mc.risk_metrics.sharpe_ratio,            color: "var(--buy)" },
                      { label: "P(Loss)",  value: mc.risk_metrics.probability_of_loss,     color: "var(--hold)" },
                    ].map(({ label, value, color }) => (
                      <div key={label} className="flex flex-col items-center p-2 rounded"
                        style={{ background: "var(--bg-void)", border: "1px solid var(--border-subtle)" }}>
                        <span className="section-label">{label}</span>
                        <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "14px", fontWeight: 800, color }}>
                          {value != null ? value.toFixed(2) : "—"}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 space-y-1">
                    <div className="flex justify-between">
                      <span className="section-label">MEDIAN (30D)</span>
                      <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", color: "var(--buy)", fontWeight: 700 }}>
                        {mc.percentile_paths?.median?.slice(-1)[0]?.toFixed(2) ?? "—"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="section-label">RANGE (5–95%)</span>
                      <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", color: "var(--text-secondary)" }}>
                        {mc.percentile_paths?.lower_05?.slice(-1)[0]?.toFixed(2) ?? "—"} – {mc.percentile_paths?.upper_95?.slice(-1)[0]?.toFixed(2) ?? "—"}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
