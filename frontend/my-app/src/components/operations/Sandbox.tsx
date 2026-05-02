import React, { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { sandboxApi } from "../../api";
import { useUIStore } from "../../store";
import { Sliders, Activity, AlertCircle, Play, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

export default function Sandbox() {
  const { user } = useUIStore();
  const [scenarioName, setScenarioName] = useState("Hormuz Strait Closure");
  const [region, setRegion] = useState("Middle East");
  const [eventType, setEventType] = useState("energy");
  const [magnitude, setMagnitude] = useState("High");
  
  // Timeline progress animation states
  const [simStep, setSimStep] = useState(0);
  const [isSimulating, setIsSimulating] = useState(false);

  // Fetch recent simulations
  const { data: simulations, refetch: refetchSimulations } = useQuery({
    queryKey: ["simulations-history"],
    queryFn: () => sandboxApi.getSimulations(),
  });

  // Run scenario simulation mutation
  const runSimulationMutation = useMutation({
    mutationFn: (payload: any) => sandboxApi.runScenario(payload),
    onSuccess: () => {
      toast.success("Simulation finished successfully.");
      refetchSimulations();
      setIsSimulating(false);
      setSimStep(0);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || "Simulation run failed.";
      toast.error(msg);
      setIsSimulating(false);
      setSimStep(0);
    }
  });

  const handleRunSimulation = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSimulating(true);
    setSimStep(1);

    let current = 1;
    const interval = setInterval(() => {
      current += 1;
      if (current <= 4) {
        setSimStep(current);
      } else {
        clearInterval(interval);
        // Trigger the actual API call
        runSimulationMutation.mutate({
          scenario_name: scenarioName,
          region,
          event_type: eventType,
          magnitude,
          user_id: user?.id
        });
      }
    }, 1500);
  };

  const getStepText = (step: number) => {
    switch (step) {
      case 1: return "1. ANALYZING DEPENDENCIES...";
      case 2: return "2. CALCULATING RISK EXPOSURE...";
      case 3: return "3. RUNNING FORECAST MODELLING...";
      case 4: return "4. GENERATING REPORT SHEETS...";
      default: return "";
    }
  };

  const activeResult = runSimulationMutation.data?.data;

  return (
    <div className="flex flex-1 h-full bg-bg-primary overflow-hidden pt-14 select-none">
      {/* Left Column: Scenario Builder */}
      <div className="w-80 border-r border-border-primary bg-bg-secondary p-5 flex flex-col h-full overflow-y-auto">
        <div className="flex items-center gap-2 mb-4 border-b border-border-primary pb-3">
          <Sliders className="w-4 h-4 text-accent-primary" />
          <span className="font-mono text-xs font-bold uppercase tracking-widest text-text-primary">
            Scenario Builder
          </span>
        </div>

        <form onSubmit={handleRunSimulation} className="space-y-4 font-mono text-xs">
          <div>
            <label className="block text-text-muted uppercase tracking-wider mb-1.5">Scenario Name</label>
            <input
              type="text"
              required
              value={scenarioName}
              onChange={(e) => setScenarioName(e.target.value)}
              className="w-full px-3 py-2 bg-bg-primary border border-border-primary rounded text-text-primary focus:outline-none focus:border-accent-primary"
            />
          </div>

          <div>
            <label className="block text-text-muted uppercase tracking-wider mb-1.5">Geographic Region</label>
            <select
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              className="w-full px-3 py-2 bg-bg-primary border border-border-primary rounded text-text-primary focus:outline-none focus:border-accent-primary"
            >
              <option value="Middle East">MIDDLE EAST</option>
              <option value="East Asia">EAST ASIA</option>
              <option value="Eastern Europe">EASTERN EUROPE</option>
              <option value="Global">GLOBAL</option>
            </select>
          </div>

          <div>
            <label className="block text-text-muted uppercase tracking-wider mb-1.5">Incident Type</label>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="w-full px-3 py-2 bg-bg-primary border border-border-primary rounded text-text-primary focus:outline-none focus:border-accent-primary"
            >
              <option value="war">WAR &amp; SECURITY</option>
              <option value="conflict">CONFLICT OPERATIONS</option>
              <option value="sanctions">ECONOMIC SANCTIONS</option>
              <option value="cyber">CYBER WARFARE</option>
              <option value="energy">ENERGY DISRUPTIONS</option>
            </select>
          </div>

          <div>
            <label className="block text-text-muted uppercase tracking-wider mb-1.5">Disruption Magnitude</label>
            <select
              value={magnitude}
              onChange={(e) => setMagnitude(e.target.value)}
              className="w-full px-3 py-2 bg-bg-primary border border-border-primary rounded text-text-primary focus:outline-none focus:border-accent-primary"
            >
              <option value="Low">LOW</option>
              <option value="Moderate">MODERATE</option>
              <option value="High">HIGH</option>
              <option value="Severe">SEVERE</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={isSimulating}
            className="flex items-center justify-center gap-2 w-full py-2.5 bg-accent-primary hover:bg-blue-600 disabled:bg-border-primary text-text-primary font-bold uppercase rounded cursor-pointer transition-colors"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>{isSimulating ? "Simulating..." : "Trigger Sandbox"}</span>
          </button>
        </form>
      </div>

      {/* Center & Right Column Workspace */}
      <div className="flex-1 flex flex-col p-6 overflow-y-auto space-y-6">
        <div className="flex items-center gap-2 border-b border-border-primary pb-3">
          <Activity className="w-5 h-5 text-accent-primary" />
          <h2 className="font-mono text-sm font-bold text-text-primary uppercase tracking-wider">
            Geopolitical Simulation Terminal &amp; Metrics
          </h2>
        </div>

        {/* Dynamic Interactive Progress / Results Workspace */}
        {isSimulating ? (
          <div className="p-8 border border-border-primary bg-bg-secondary rounded-md flex flex-col justify-center items-center h-80 space-y-4">
            <div className="w-12 h-12 border-4 border-accent-secondary border-t-transparent rounded-full animate-spin"></div>
            <div className="font-mono text-xs text-accent-secondary font-bold tracking-widest uppercase animate-pulse">
              {getStepText(simStep)}
            </div>
            <div className="text-[10px] font-mono text-text-muted">
              SYSTEM MODELLING MONTE CARLO PRICE FORECAST DRIFTS...
            </div>
          </div>
        ) : activeResult ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Impact Heatmap / Price changes */}
            <div className="p-5 border border-border-primary bg-surface rounded-md flex flex-col space-y-4">
              <div className="flex items-center gap-2 border-b border-border-primary pb-2 text-text-primary">
                <CheckCircle2 className="w-4 h-4 text-risk-low" />
                <span className="font-mono text-xs font-bold uppercase tracking-wider">Asset Impact Projections</span>
              </div>
              <div className="space-y-3 font-mono text-xs">
                {Object.entries(activeResult.affected_assets || {}).map(([symbol, item]: any) => {
                  const pct = item.impact_pct;
                  const isUp = item.direction === "UP";
                  return (
                    <div key={symbol} className="flex justify-between items-center p-2 border border-border-primary bg-bg-primary rounded">
                      <div>
                        <div className="font-bold text-text-primary">{symbol}</div>
                        <div className="text-[10px] text-text-muted leading-tight mt-0.5">{item.reason}</div>
                      </div>
                      <span className={`px-2 py-0.5 rounded font-bold ${isUp ? "text-risk-low bg-risk-low/5" : "text-risk-critical bg-risk-critical/5"}`}>
                        {isUp ? "+" : ""}{pct.toFixed(2)}%
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Simulated Sector Vulnerability and report */}
            <div className="p-5 border border-border-primary bg-surface rounded-md flex flex-col space-y-4">
              <div className="flex items-center gap-2 border-b border-border-primary pb-2 text-text-primary">
                <AlertCircle className="w-4 h-4 text-accent-primary" />
                <span className="font-mono text-xs font-bold uppercase tracking-wider">Simulation Intelligence Report</span>
              </div>
              <div className="space-y-4 font-sans text-xs text-text-secondary leading-relaxed">
                <div>
                  <div className="font-mono text-[9px] text-text-muted uppercase mb-1">Executive Summary</div>
                  <p className="p-3 border border-border-primary bg-bg-primary rounded font-medium text-text-primary">
                    {activeResult.summary}
                  </p>
                </div>
                <div>
                  <div className="font-mono text-[9px] text-text-muted uppercase mb-2">Sector exposure impacts</div>
                  <div className="grid grid-cols-2 gap-2.5 font-mono text-[10px] text-text-secondary">
                    {Object.entries(activeResult.sector_impacts || {}).map(([sector, desc]: any) => (
                      <div key={sector} className="p-2 border border-border-primary bg-bg-primary rounded">
                        <span className="text-accent-secondary uppercase font-bold">{sector}</span>
                        <p className="text-[9px] text-text-muted mt-1 leading-snug">{desc}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-8 border border-dashed border-border-primary rounded-md flex flex-col justify-center items-center h-80 text-text-muted">
            <Sliders className="w-8 h-8 mb-3 text-text-muted" />
            <div className="font-mono text-xs uppercase tracking-wider">Awaiting Simulation</div>
            <div className="text-[10px] mt-1">Configure parameters and click "Trigger Sandbox".</div>
          </div>
        )}

        {/* History Table */}
        <div className="p-5 border border-border-primary bg-surface rounded-md">
          <div className="border-b border-border-primary pb-3 mb-3">
            <h3 className="font-mono text-xs font-bold text-text-primary uppercase tracking-wider">Recent Simulation Runs</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left sios-table">
              <thead>
                <tr>
                  <th>Scenario</th>
                  <th>Region</th>
                  <th>Type</th>
                  <th>Magnitude</th>
                  <th>Risk Level</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody className="font-mono text-xs">
                {simulations?.data?.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-6 text-text-muted">No historical runs recorded</td>
                  </tr>
                ) : (
                  simulations?.data?.slice(0, 5).map((s: any) => (
                    <tr key={s.id}>
                      <td className="font-sans font-medium text-text-primary">{s.scenario_name}</td>
                      <td>{s.region}</td>
                      <td>{s.event_type}</td>
                      <td>{s.magnitude}</td>
                      <td>{s.risk_level}</td>
                      <td className="text-text-muted text-[10px] tabular-nums">
                        {new Date(s.timestamp || s.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
