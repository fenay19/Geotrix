import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useMutation } from "@tanstack/react-query";
import { marketApi, riskApi } from "../../api";
import {
  Settings, Play, Terminal, Search, Cpu,
  Sliders, Activity
} from "lucide-react";
import { toast } from "sonner";
import Sandbox from "./Sandbox";
import SupplyChain from "./SupplyChain";

// ── Helpers ────────────────────────────────────────────────────────────────────
const LOG_LEVELS: Record<string, string> = {
  INFO:    "var(--buy)",
  ERROR:   "var(--sell)",
  WARNING: "var(--hold)",
  DEBUG:   "var(--text-muted)",
};

const TABS = [
  { id: "supply",  label: "Supply Chain",  icon: Settings },
  { id: "sandbox", label: "Scenario Sandbox", icon: Sliders  },
  { id: "system",  label: "System Health",  icon: Activity },
];

// Supply Chain tab now uses the ForceGraph2D component from SupplyChain.tsx

// ── System Health Tab ──────────────────────────────────────────────────────────
const SYSTEM_NODES = [
  { label: "ML Universal Model",    status: "ONLINE",  color: "var(--buy)" },
  { label: "Monte Carlo Engine",    status: "ONLINE",  color: "var(--buy)" },
  { label: "Vector Store (RAG)",    status: "ONLINE",  color: "var(--buy)" },
  { label: "Groq LLM Node",         status: "STANDBY", color: "var(--hold)" },
  { label: "WebSocket Broadcaster", status: "ONLINE",  color: "var(--buy)" },
  { label: "Background Scheduler",  status: "ONLINE",  color: "var(--buy)" },
  { label: "Finnhub Market Feed",   status: "ACTIVE",  color: "var(--buy)" },
  { label: "News RSS Ingestion",    status: "ONLINE",  color: "var(--buy)" },
];

function SystemHealthTab() {
  const [logs, setLogs] = useState<string[]>([
    "2026-06-11 00:00:01 [INFO] geotrade.scheduler — Background sync scheduler active.",
    "2026-06-11 00:00:15 [INFO] geotrade.pipelines.market — Synced GOLD, OIL_BRENT, SP500, BTCUSD prices.",
    "2026-06-11 00:05:00 [INFO] geotrade.pipelines.news — Executing news ingestion scan.",
    "2026-06-11 00:05:12 [INFO] geotrade.services.news — BBC World RSS: 38 articles retrieved.",
    "2026-06-11 00:05:14 [INFO] geotrade.services.news — Al Jazeera RSS: 25 articles retrieved.",
    "2026-06-11 00:05:32 [INFO] geotrade.pipelines.news — Accepted 2 high-relevance events.",
    "2026-06-11 00:05:41 [INFO] geotrade.services.gti — Calculated GTI: 45.2 (MODERATE).",
    "2026-06-11 00:05:42 [INFO] geotrade.ws — Broadcasting GTI update to connected consoles.",
  ]);
  const [search, setSearch] = useState("");
  const terminalRef = useRef<HTMLDivElement>(null);

  const appendLog = (msg: string) => {
    const ts = new Date().toISOString().replace("T", " ").substring(0, 19);
    setLogs(prev => [...prev.slice(-100), `${ts} ${msg}`]);
  };

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  const syncMarketsMutation = useMutation({
    mutationFn: () => marketApi.syncMarketData(15),
    onSuccess: (resp) => {
      toast.success("Market pipeline complete.");
      appendLog(`[INFO] geotrade.pipelines.market — Sync complete: ${JSON.stringify(resp.data)}`);
    },
    onError: () => {
      toast.error("Market pipeline failed.");
      appendLog("[ERROR] geotrade.pipelines.market — Sync failed.");
    },
  });

  const syncRiskMutation = useMutation({
    mutationFn: () => riskApi.syncGlobalRisk(true),
    onSuccess: (resp) => {
      toast.success("Risk pipeline complete.");
      appendLog(`[INFO] geotrade.pipelines.risk — GTI Score: ${resp.data?.new_gti ?? "updated"}`);
    },
    onError: () => {
      toast.error("Risk pipeline failed.");
      appendLog("[ERROR] geotrade.pipelines.risk — Sync failed.");
    },
  });

  const filteredLogs = logs.filter(l => !search || l.toLowerCase().includes(search.toLowerCase()));

  const getLogColor = (log: string) => {
    for (const [level, color] of Object.entries(LOG_LEVELS)) {
      if (log.includes(`[${level}]`)) return color;
    }
    return "var(--text-secondary)";
  };

  return (
    <div className="flex h-full overflow-hidden gap-0">
      {/* Left: node status */}
      <div className="flex flex-col border-r overflow-hidden shrink-0 p-5 gap-4"
        style={{ width: 300, borderColor: "var(--border)", backgroundColor: "var(--bg-secondary)" }}>
        <span className="section-label" style={{ color: "var(--amber)" }}>SERVICE STATUS</span>
        <div className="space-y-2">
          {SYSTEM_NODES.map((n, i) => (
            <motion.div
              key={n.label}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="flex items-center justify-between px-3 py-2.5"
              style={{ background: "var(--bg-void)", border: "1px solid var(--border-subtle)", borderRadius: 1 }}
            >
              <div className="flex items-center gap-2">
                <Cpu size={11} style={{ color: n.color }} />
                <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "10px", color: "var(--text-secondary)", fontWeight: 700 }}>
                  {n.label}
                </span>
              </div>
              <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "9px", fontWeight: 700, color: n.color }}>
                {n.status}
              </span>
            </motion.div>
          ))}
        </div>

        {/* Pipeline triggers */}
        <div className="mt-2">
          <span className="section-label mb-3 block">MANUAL TRIGGERS</span>
          <div className="space-y-2">
            {[
              { label: "MARKET SYNC",   mutation: syncMarketsMutation },
              { label: "RISK SYNC",     mutation: syncRiskMutation },
            ].map(({ label, mutation }) => (
              <button
                key={label}
                onClick={() => mutation.mutate()}
                disabled={mutation.isPending}
                className="btn-amber w-full"
                style={{ opacity: mutation.isPending ? 0.5 : 1 }}
              >
                <Play size={11} />
                {mutation.isPending ? "RUNNING..." : `RUN ${label}`}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Right: terminal */}
      <div className="flex-1 flex flex-col overflow-hidden p-5">
        <div className="flex items-center justify-between mb-3 shrink-0">
          <div className="flex items-center gap-2">
            <Terminal size={12} style={{ color: "var(--amber)" }} />
            <span className="section-label" style={{ color: "var(--amber)" }}>SYSTEM TERMINAL</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5"
            style={{ background: "var(--bg-void)", border: "1px solid var(--border)", borderRadius: 1 }}>
            <Search size={10} style={{ color: "var(--text-muted)" }} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter logs..."
              style={{
                background: "transparent", border: "none", outline: "none",
                fontFamily: "'Space Mono', monospace", fontSize: "10px",
                color: "var(--text-primary)", width: 140,
              }}
            />
          </div>
        </div>
        <div
          ref={terminalRef}
          className="flex-1 overflow-y-auto p-4"
          style={{ background: "var(--bg-void)", border: "1px solid var(--border)", borderRadius: 1, fontFamily: "'Space Mono', monospace", fontSize: "10px", lineHeight: 1.8 }}
        >
          {filteredLogs.map((log, i) => (
            <div key={i} style={{ color: getLogColor(log) }}>
              {log}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Main Operations Component ──────────────────────────────────────────────────
export default function Operations() {
  const [activeTab, setActiveTab] = useState("supply");

  return (
    <div className="flex flex-col h-full overflow-hidden select-none"
      style={{ backgroundColor: "var(--bg-primary)" }}>
      {/* Tab header */}
      <motion.div
        initial={{ y: -16, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="flex items-center gap-0 border-b shrink-0 px-4"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-secondary)" }}
      >
        <div className="flex items-center gap-2 pr-6 border-r mr-2" style={{ borderColor: "var(--border)", paddingTop: 8, paddingBottom: 8 }}>
          <Settings size={13} style={{ color: "var(--amber)" }} />
          <span className="section-label" style={{ color: "var(--amber)" }}>OPERATIONS</span>
        </div>
        {TABS.map((t) => {
          const Icon = t.icon;
          const active = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className="flex items-center gap-2 px-5 py-3 cursor-pointer transition-all"
              style={{
                fontFamily: "'Space Mono', monospace",
                fontSize: "10px",
                fontWeight: 700,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                color: active ? "var(--amber)" : "var(--text-muted)",
                borderBottom: active ? "2px solid var(--amber)" : "2px solid transparent",
                backgroundColor: "transparent",
                border: "none",
                cursor: "pointer",
                borderBottomStyle: "solid",
                borderBottomWidth: 2,
                borderBottomColor: active ? "var(--amber)" : "transparent",
              }}
            >
              <Icon size={11} style={{ color: active ? "var(--amber)" : "var(--text-muted)" }} />
              {t.label}
            </button>
          );
        })}
      </motion.div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            {activeTab === "supply"  && <SupplyChain />}
            {activeTab === "sandbox" && <Sandbox />}
            {activeTab === "system"  && <SystemHealthTab />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
