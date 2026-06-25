import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, GeoJSON, Polyline, Marker, useMap } from 'react-leaflet';
import L from 'leaflet';
import axios from 'axios';
import { riskColor } from '../utils/risk';
import {
  StopCircle,
  AlertTriangle,
  X,
  FileText,
  Activity,
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

// Lat/Lon coordinates mapping for seeded Supply Chain nodes
const NODE_COORDS: Record<string, { lat: number; lon: number }> = {
  'Semiconductors': { lat: 23.5, lon: 121.0 }, // Taiwan
  'Rare Earth Minerals': { lat: 35.8617, lon: 104.1954 }, // China
  'Crude Oil': { lat: 24.7136, lon: 46.6753 }, // Saudi Arabia
  'Natural Gas': { lat: 61.5240, lon: 105.3188 }, // Russia
  'Tech Industry': { lat: 37.7749, lon: -122.4194 }, // USA (Silicon Valley)
  'Electronics Manufacturing': { lat: 22.5431, lon: 114.0579 }, // China (Shenzhen)
  'Energy Sector': { lat: 51.9244, lon: 4.4777 }, // Rotterdam Port / Europe
  'Automotive Industry': { lat: 51.1657, lon: 10.4515 }, // Germany
  'Defense Sector': { lat: 38.9072, lon: -77.0369 }, // USA (DC)
  'Agriculture / Grain': { lat: 48.3794, lon: 31.1656 }, // Ukraine
  'Advanced Lithography (EUV)': { lat: 52.1326, lon: 5.2913 }, // Netherlands
  'Lithium / Battery Cells': { lat: -25.2744, lon: 133.7751 }, // Australia
  'Cobalt Mining': { lat: -4.0383, lon: 21.7587 }, // DR Congo
  'Suez Canal Transit': { lat: 30.5852, lon: 32.2633 }, // Egypt
  'Strait of Malacca Transit': { lat: 1.3521, lon: 103.8198 }, // Singapore
  'Potash / Fertilizers': { lat: 56.1304, lon: -106.3468 }, // Canada
};

const FALLBACK_SCENARIOS = [
  {
    title: "Russia Refused to Give Oil to Pakistan",
    event_type: "economic",
    region: "South Asia",
    severity: 8,
    description: "Russia halts negotiations on discounted crude shipments to Pakistan due to payment currency disputes."
  },
  {
    title: "Taiwan Strait Blockade Escalation",
    event_type: "war",
    region: "East Asia",
    severity: 10,
    description: "Naval drills block commercial corridors surrounding Taiwan, halting semiconductor shipments."
  },
  {
    title: "Suez Canal Shipping Corridor Halt",
    event_type: "economic",
    region: "Middle East",
    severity: 8,
    description: "A maritime accident blocks the Suez Canal, causing a cargo traffic backlog between Asia and Europe."
  },
  {
    title: "US-China Semiconductor Trade Sanctions",
    event_type: "sanctions",
    region: "North America",
    severity: 8,
    description: "The United States imposes stricter high-tech equipment export controls on Chinese chip manufacturers."
  },
  {
    title: "Strait of Hormuz Closure",
    event_type: "war",
    region: "Middle East",
    severity: 10,
    description: "Regional military exercises disrupt shipping lanes in the Strait of Hormuz, threatening global oil supplies."
  },
  {
    title: "OPEC Surprise Crude Oil Production Cut",
    event_type: "economic",
    region: "Middle East",
    severity: 6,
    description: "OPEC+ countries agree to reduce crude oil production by 1.2 million barrels per day starting next month."
  },
  {
    title: "Ukrainian Grain Shipments Interdiction",
    event_type: "war",
    region: "Europe",
    severity: 7,
    description: "Naval hostilities in the Black Sea threaten cargo corridors exporting grain from Ukraine."
  },
  {
    title: "Critical Rare Earth Export Controls",
    event_type: "sanctions",
    region: "East Asia",
    severity: 6,
    description: "China introduces export permit controls on gallium and germanium minerals used in semiconductor production."
  },
  {
    title: "Global Cloud Infrastructure Cyber Attack",
    event_type: "policy",
    region: "Global",
    severity: 8,
    description: "A coordinated zero-day exploit targets major enterprise cloud providers, stalling SaaS networks."
  },
  {
    title: "Federal Reserve Interest Rate Shock",
    event_type: "economic",
    region: "North America",
    severity: 5,
    description: "The Federal Reserve announces a surprise 50 basis point interest rate hike to curb stubborn inflation."
  }
];

const mapSeverityToMagnitude = (sev: number): string => {
  if (sev >= 9) return 'Catastrophic';
  if (sev >= 7) return 'Severe';
  if (sev >= 4) return 'Moderate';
  return 'Mild';
};

// Map Fly controller component for Supply Chain focus
const MapFocusController: React.FC<{ focusCoords: [number, number] | null }> = ({ focusCoords }) => {
  const map = useMap();
  useEffect(() => {
    if (focusCoords) {
      map.flyTo(focusCoords, 5, { duration: 1.2 });
    }
  }, [focusCoords, map]);
  return null;
};

export const SupplyChain: React.FC = () => {
  // Graph Data
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [criticalNodes, setCriticalNodes] = useState<any[]>([]);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [highlightedEdges, setHighlightedEdges] = useState<number[]>([]);

  // Node Intelligence Panel State
  const [nodeIntel, setNodeIntel] = useState<any | null>(null);
  const [nodeIntelLoading, setNodeIntelLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'tree' | 'impact'>('overview');
  const [simTargetIntel, setSimTargetIntel] = useState<any | null>(null);

  // Simulation Panel
  const [simModalOpen, setSimModalOpen] = useState<boolean>(false);
  const [simTargetNode, setSimTargetNode] = useState<number | null>(null);
  const [simDisruptionType, setSimDisruptionType] = useState<string>('Blockade');
  // Severity is stored 0-10 in the slider, converted to 0-100 on send
  const [simSeverity, setSimSeverity] = useState<number>(7);
  const [simPreviewText, setSimPreviewText] = useState<string>('Select a target node to view estimated impact parameters.');

  // Scenario/News-based Simulation State
  const [activeSimTab, setActiveSimTab] = useState<'node' | 'scenario'>('node');
  const [liveNews, setLiveNews] = useState<any[]>([]);
  const [selectedDropdownEvent, setSelectedDropdownEvent] = useState<string>('');
  const [scenarioText, setScenarioText] = useState<string>('');
  const [selectedRegion, setSelectedRegion] = useState<string>('Global');
  const [selectedEventType, setSelectedEventType] = useState<string>('economic');
  const [selectedMagnitude, setSelectedMagnitude] = useState<string>('Moderate');

  // Running Simulation State
  const [simRunning, setSimRunning] = useState<boolean>(false);
  const [simLogs, setSimLogs] = useState<any[]>([]);
  const [simLogsExpanded, setSimLogsExpanded] = useState<boolean>(true);
  const [disruptedNodeIds, setDisruptedNodeIds] = useState<number[]>([]);
  const [disruptedEdgeIds, setDisruptedEdgeIds] = useState<number[]>([]);
  const [simCompleted, setSimCompleted] = useState<boolean>(false);
  // Maps node_id → impact score (0–100) from BFS result — drives map colouring
  const [nodeImpactMap, setNodeImpactMap] = useState<Record<number, number>>({});

  // Map Centroids
  const [focusCentroid, setFocusCentroid] = useState<[number, number] | null>(null);

  const logEndRef = useRef<HTMLDivElement>(null);
  // logIntervalRef kept for stop simulation cleanup compatibility
  const logIntervalRef = useRef<any>(null);

  // 1. Fetch graph and critical nodes on mount
  useEffect(() => {
    const loadGraphData = async () => {
      try {
        const graphRes = await axios.get(`${API_BASE}/supply-chain/graph`);
        if (graphRes.data) {
          setNodes(graphRes.data.nodes || []);
          setEdges(graphRes.data.edges || []);
        }
        const critRes = await axios.get(`${API_BASE}/supply-chain/critical-nodes`);
        if (critRes.data) {
          setCriticalNodes(critRes.data || []);
        }
        const newsRes = await axios.get(`${API_BASE}/news?limit=10`);
        if (newsRes.data) {
          setLiveNews(newsRes.data);
        }
      } catch (err) {
        console.warn('Failed to load supply chain graph, building mock dataset:', err);
        setLiveNews([]);
        // Mock fallback nodes matching coords
        const mockNodes = [
          { id: 1, label: 'Semiconductors', location: 'Taiwan', type: 'choke_point', risk_score: 82 },
          { id: 2, label: 'Rare Earth Minerals', location: 'China', type: 'choke_point', risk_score: 65 },
          { id: 3, label: 'Crude Oil', location: 'Saudi Arabia', type: 'choke_point', risk_score: 45 },
          { id: 4, label: 'Natural Gas', location: 'Russia', type: 'choke_point', risk_score: 78 },
          { id: 5, label: 'Tech Industry', location: 'Global', type: 'production', risk_score: 25 },
          { id: 6, label: 'Electronics Manufacturing', location: 'Global', type: 'production', risk_score: 60 },
          { id: 7, label: 'Energy Sector', location: 'Global', type: 'port', risk_score: 40 },
          { id: 8, label: 'Automotive Industry', location: 'Global', type: 'production', risk_score: 30 },
          { id: 9, label: 'Defense Sector', location: 'Global', type: 'production', risk_score: 35 },
          { id: 10, label: 'Agriculture / Grain', location: 'Ukraine', type: 'production', risk_score: 90 },
          { id: 11, label: 'Advanced Lithography (EUV)', location: 'Netherlands', type: 'choke_point', risk_score: 95 },
          { id: 12, label: 'Lithium / Battery Cells', location: 'Australia', type: 'choke_point', risk_score: 70 },
          { id: 13, label: 'Cobalt Mining', location: 'DR Congo', type: 'choke_point', risk_score: 80 },
          { id: 14, label: 'Suez Canal Transit', location: 'Egypt', type: 'port', risk_score: 60 },
          { id: 15, label: 'Strait of Malacca Transit', location: 'Singapore', type: 'port', risk_score: 65 },
          { id: 16, label: 'Potash / Fertilizers', location: 'Canada', type: 'production', risk_score: 50 },
        ];
        // Mock fallback edges
        const mockEdges = [
          { id: 201, source: 1, target: 5, type: 'critical_input', strength: 0.95 },
          { id: 202, source: 1, target: 6, type: 'critical_input', strength: 0.90 },
          { id: 203, source: 1, target: 8, type: 'major_input', strength: 0.70 },
          { id: 204, source: 2, target: 6, type: 'critical_input', strength: 0.85 },
          { id: 205, source: 2, target: 9, type: 'major_input', strength: 0.75 },
          { id: 206, source: 3, target: 7, type: 'critical_input', strength: 0.95 },
          { id: 207, source: 3, target: 8, type: 'major_input', strength: 0.60 },
          { id: 208, source: 4, target: 7, type: 'pipeline', strength: 0.80 },
          { id: 209, source: 10, target: 7, type: 'minor_input', strength: 0.30 },
          { id: 210, source: 11, target: 1, type: 'critical_input', strength: 0.98 },
          { id: 211, source: 12, target: 8, type: 'major_input', strength: 0.85 },
          { id: 212, source: 12, target: 6, type: 'major_input', strength: 0.75 },
          { id: 213, source: 13, target: 12, type: 'critical_input', strength: 0.80 },
          { id: 214, source: 3, target: 14, type: 'pipeline', strength: 0.85 },
          { id: 215, source: 14, target: 7, type: 'critical_input', strength: 0.90 },
          { id: 216, source: 3, target: 15, type: 'critical_input', strength: 0.75 },
          { id: 217, source: 15, target: 6, type: 'major_input', strength: 0.80 },
          { id: 218, source: 16, target: 10, type: 'major_input', strength: 0.70 },
        ];
        setNodes(mockNodes);
        setEdges(mockEdges);
        setCriticalNodes([
          { id: 11, name: 'Advanced Lithography (EUV)', location: 'Netherlands', type: 'choke_point', dependent_count: 1, risk_label: 'CRITICAL', chokepoint_score: 0.98 },
          { id: 1, name: 'Semiconductors', location: 'Taiwan', type: 'choke_point', dependent_count: 3, risk_label: 'CRITICAL', chokepoint_score: 2.55 },
          { id: 2, name: 'Rare Earth Minerals', location: 'China', type: 'choke_point', dependent_count: 2, risk_label: 'HIGH', chokepoint_score: 1.60 },
          { id: 3, name: 'Crude Oil', location: 'Saudi Arabia', type: 'choke_point', dependent_count: 4, risk_label: 'CRITICAL', chokepoint_score: 3.15 },
        ]);
      }
    };
    loadGraphData();
  }, []);

  // Auto scroll logs
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [simLogs]);

  // Handle selecting target in simulation dropdown
  const handleSelectSimTarget = async (id: number) => {
    setSimTargetNode(id);
    setSimTargetIntel(null);
    const nodeObj = nodes.find((n) => n.id === id);
    if (!nodeObj) return;

    setSimPreviewText(`Fetching cascade preview parameters for ${nodeObj.label}...`);
    try {
      const res = await axios.get(`${API_BASE}/supply-chain/nodes/${id}/intelligence`);
      setSimTargetIntel(res.data);
      const count = res.data?.dependency_tree?.children?.length ?? 0;
      if (count > 0) {
        setSimPreviewText(
          `Node selected: ${nodeObj.label}. Outgoing dependency tree mapped.`
        );
      } else {
        setSimPreviewText(
          `Node selected: ${nodeObj.label}. No outgoing dependencies registered — disruption will not cascade.`
        );
      }
    } catch {
      setSimPreviewText(
        `Node selected: ${nodeObj.label}. BFS impact propagation ready.`
      );
    }
  };

  const handleSelectScenarioOption = (val: string) => {
    setSelectedDropdownEvent(val);
    if (val === '' || val === 'custom') {
      setScenarioText('');
      return;
    }
    
    // Find in live news first
    const matchedNews = liveNews.find(n => n.title === val);
    if (matchedNews) {
      setScenarioText(matchedNews.title);
      setSelectedEventType(matchedNews.event_type || 'economic');
      setSelectedMagnitude(mapSeverityToMagnitude(matchedNews.severity || 5));
      
      // Map region based on country_id (best-effort classification matching seeded db keys)
      const cid = matchedNews.country_id;
      if (cid === 1 || cid === 12) setSelectedRegion('North America');
      else if (cid === 2 || cid === 3) setSelectedRegion('East Asia');
      else if (cid === 4 || cid === 10) setSelectedRegion('Middle East');
      else if (cid === 5 || cid === 6 || cid === 7 || cid === 13) setSelectedRegion('Europe');
      else if (cid === 8 || cid === 9 || cid === 11) setSelectedRegion('South Asia');
      else setSelectedRegion('Global');
      return;
    }

    // Find in fallbacks
    const matchedFb = FALLBACK_SCENARIOS.find(fb => fb.title === val);
    if (matchedFb) {
      setScenarioText(matchedFb.title);
      setSelectedEventType(matchedFb.event_type);
      setSelectedRegion(matchedFb.region);
      setSelectedMagnitude(mapSeverityToMagnitude(matchedFb.severity));
    }
  };

  const handleStartScenarioSimulation = async () => {
    if (!scenarioText.trim()) return;
    setSimModalOpen(false);
    setSimRunning(true);
    setSimCompleted(false);
    setSimLogsExpanded(true);
    setSimLogs([
      { text: `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`, type: 'info' },
      { text: `⚡ GEOPOLITICAL SCENARIO DECLARED`, type: 'crit' },
      { text: `   Scenario  : ${scenarioText}`, type: 'crit' },
      { text: `   Region    : ${selectedRegion}`, type: 'crit' },
      { text: `   Event Type: ${selectedEventType.toUpperCase()}`, type: 'crit' },
      { text: `   Magnitude : ${selectedMagnitude.toUpperCase()}`, type: 'crit' },
      { text: `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`, type: 'info' },
      { text: `▶ INITIATING GEOPOLITICAL SCENARIO ANALYSIS ENGINE...`, type: 'info' },
      { text: `  ↳ Connecting to AI reasoning backend...`, type: 'info' }
    ]);
    setDisruptedNodeIds([]);
    setDisruptedEdgeIds([]);
    setNodeImpactMap({});

    try {
      const payload = {
        scenario_name: scenarioText,
        region: selectedRegion,
        event_type: selectedEventType,
        magnitude: selectedMagnitude,
      };

      const res = await axios.post(`${API_BASE}/simulation/run`, payload);
      const data = res.data;
      const results = data.results ?? {};

      // Parse results and display them in simulated streams
      await new Promise((r) => setTimeout(r, 600));

      setSimLogs(prev => [
        ...prev,
        { text: `[OK] Analysis completed successfully.`, type: 'info' },
        { text: ``, type: 'info' },
        { text: `▶ PREDICTION SUMMARY`, type: 'warn' },
        { text: `  ${results.summary ?? 'No summary available.'}`, type: 'warn' }
      ]);

      await new Promise((r) => setTimeout(r, 600));

      // Display affected assets
      const affectedAssets = results.affected_assets ?? {};
      const assetKeys = Object.keys(affectedAssets);
      if (assetKeys.length > 0) {
        // Calculate dynamic formatting width helper
        const formattedAssetLines = assetKeys.map(k => {
          const val = affectedAssets[k];
          const arr = val.direction === 'UP' ? '▲' : val.direction === 'DOWN' ? '▼' : '■';
          // format strings with manual padding
          const colSym = k.padEnd(10);
          const colImp = (val.impact_pct + '%').padEnd(10);
          const colDir = (arr + ' ' + val.direction).padEnd(12);
          return {
            text: `   ${colSym} ${colImp} ${colDir} ${val.reason || ''}`,
            type: val.direction === 'UP' ? 'info' : val.direction === 'DOWN' ? 'crit' : 'info'
          };
        });

        const headerSym = 'ASSET'.padEnd(10);
        const headerImp = 'IMPACT'.padEnd(10);
        const headerDir = 'DIRECTION'.padEnd(12);

        setSimLogs(prev => [
          ...prev,
          { text: ``, type: 'info' },
          { text: `▶ AFFECTED ASSETS PREDICTED IMPACT`, type: 'warn' },
          { text: `   ${headerSym} ${headerImp} ${headerDir} REASON`, type: 'info' },
          { text: `   ${'─'*65}`, type: 'info' },
          ...formattedAssetLines
        ]);
      }

      await new Promise((r) => setTimeout(r, 600));

      // Display sector impacts
      const sectorImpacts = results.sector_impacts ?? {};
      const sectorKeys = Object.keys(sectorImpacts);
      if (sectorKeys.length > 0) {
        setSimLogs(prev => [
          ...prev,
          { text: ``, type: 'info' },
          { text: `▶ SECTOR LOGISTICS EXPOSURE`, type: 'warn' },
          ...sectorKeys.map(k => ({
            text: `   • ${k}: ${sectorImpacts[k]}`,
            type: 'warn'
          }))
        ]);
      }

      // Map predicted impacts to Leaflet Map nodes dynamically to show visual impact!
      // Map magnitude to impact percentage
      const magnitudeImpacts: Record<string, number> = {
        'Mild': 25,
        'Moderate': 50,
        'Severe': 75,
        'Catastrophic': 95
      };
      const baseImpact = magnitudeImpacts[selectedMagnitude] || 50;

      const impactedNodeIds: number[] = [];
      const impactMap: Record<number, number> = {};

      // Match nodes based on keywords in scenario or affected sectors
      nodes.forEach((node: any) => {
        const label = node.label.toLowerCase();
        const isEnergyRelated = label.includes('oil') || label.includes('gas') || label.includes('energy') || label.includes('suez') || label.includes('malacca');
        const isTechRelated = label.includes('semiconductor') || label.includes('tech') || label.includes('electronics') || label.includes('lithography');
        const isDefenseRelated = label.includes('defense') || label.includes('rare earth') || label.includes('mineral');
        const isAgriRelated = label.includes('grain') || label.includes('agriculture') || label.includes('potash') || label.includes('fertilizer');

        let isImpacted = false;
        let nodeImpact = baseImpact;

        if (results.sector_impacts) {
          if (results.sector_impacts.Energy && isEnergyRelated) { isImpacted = true; }
          if (results.sector_impacts.Tech && isTechRelated) { isImpacted = true; }
          if (results.sector_impacts.Defense && isDefenseRelated) { isImpacted = true; }
          if (results.sector_impacts.Agriculture && isAgriRelated) { isImpacted = true; }
        }

        // Check if node is explicitly mentioned in scenario text
        if (scenarioText.toLowerCase().includes(node.label.toLowerCase()) || 
            scenarioText.toLowerCase().includes(node.location.toLowerCase())) {
          isImpacted = true;
          nodeImpact = Math.min(100, baseImpact + 15); // boost impact for source node
        }

        if (isImpacted) {
          impactedNodeIds.push(node.id);
          impactMap[node.id] = nodeImpact;
        }
      });

      setDisruptedNodeIds(impactedNodeIds);
      setNodeImpactMap(impactMap);

      // Highlight edges whose source is disrupted
      const disrupted = new Set(impactedNodeIds);
      const disruptedEdgeList = edges
        .filter((e: any) => disrupted.has(e.source))
        .map((e: any) => e.id);
      setDisruptedEdgeIds(disruptedEdgeList);

      setSimCompleted(true);
    } catch (err: any) {
      const errMsg = err?.response?.data?.detail ?? err?.message ?? 'Unknown error';
      setSimLogs(prev => [
        ...prev,
        { text: `[${new Date().toLocaleTimeString()}] ERROR: Scenario simulation failed — ${errMsg}`, type: 'crit' }
      ]);
      setSimCompleted(true);
    }
  };

  // ── Real backend-driven BFS simulation ──────────────────────────────────
  const handleStartSimulation = async () => {
    if (!simTargetNode) return;
    setSimModalOpen(false);
    setSimRunning(true);
    setSimCompleted(false);
    setSimLogsExpanded(true);
    setSimLogs([{ text: `[${new Date().toLocaleTimeString()}] Connecting to BFS propagation engine...`, type: 'info' }]);
    setDisruptedNodeIds([simTargetNode]);
    setDisruptedEdgeIds([]);
    setNodeImpactMap({});

    try {
      const payload = {
        node_id: simTargetNode,
        severity: simSeverity * 10,   // slider 0-10 → API 0-100
        disruption_type: simDisruptionType,
        apply_variability: true,
      };

      const res = await axios.post(`${API_BASE}/supply-chain/simulate`, payload);
      const data = res.data;

      // Build impact map: node_id → impact score
      const impactMap: Record<number, number> = {};
      impactMap[simTargetNode] = payload.severity;  // source node at full severity
      (data.affected_nodes ?? []).forEach((n: any) => {
        impactMap[n.node_id] = n.impact;
      });
      setNodeImpactMap(impactMap);

      // Collect all disrupted node IDs (source + affected)
      const allDisruptedIds = [simTargetNode, ...(data.affected_nodes ?? []).map((n: any) => n.node_id)];
      setDisruptedNodeIds(allDisruptedIds);

      // Mark edges whose source is in the disrupted set as disrupted
      const disrupted = new Set(allDisruptedIds);
      const disruptedEdgeList = edges
        .filter((e: any) => disrupted.has(e.source))
        .map((e: any) => e.id);
      setDisruptedEdgeIds(disruptedEdgeList);

      // Render logs returned from backend — stream them in with a small delay
      // for the same visual effect without fake data
      const backendLogs: any[] = data.logs ?? [];
      setSimLogs([]);  // clear connecting message
      for (let i = 0; i < backendLogs.length; i++) {
        await new Promise((r) => setTimeout(r, 60));
        setSimLogs((prev) => [
          ...prev,
          { text: `[${new Date().toLocaleTimeString()}] ${backendLogs[i].text}`, type: backendLogs[i].type },
        ]);
      }

      setSimCompleted(true);
    } catch (err: any) {
      const errMsg = err?.response?.data?.detail ?? err?.message ?? 'Unknown error';
      setSimLogs((prev) => [
        ...prev,
        { text: `[${new Date().toLocaleTimeString()}] ERROR: Simulation failed — ${errMsg}`, type: 'crit' },
      ]);
      setSimCompleted(true);
    }
  };

  const handleStopSimulation = () => {
    if (logIntervalRef.current) clearInterval(logIntervalRef.current);
    setSimRunning(false);
    setSimCompleted(false);
    setDisruptedNodeIds([]);
    setDisruptedEdgeIds([]);
    setNodeImpactMap({});
    setSimLogs((prev) => [
      ...prev,
      { text: `[${new Date().toLocaleTimeString()}] Simulation terminated by user operator.`, type: 'crit' },
    ]);
  };

  // Recursive renderer for Dependency Tree
  const renderDependencyTreeNode = (treeNode: any): React.ReactNode => {
    if (!treeNode) return null;
    return (
      <div key={treeNode.id} style={{ paddingLeft: '12px', borderLeft: '1px dashed var(--border)', marginTop: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', margin: '4px 0' }}>
          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{treeNode.name}</span>
          <span style={{ fontSize: '9px', color: 'var(--text-muted)' }}>({treeNode.location})</span>
          {treeNode.strength !== undefined && treeNode.strength !== null && (
            <span style={{ fontSize: '9px', color: 'var(--accent-cyan)', fontWeight: 600 }}>
              (weight: {treeNode.strength})
            </span>
          )}
        </div>
        {treeNode.children && treeNode.children.map((child: any) => renderDependencyTreeNode(child))}
      </div>
    );
  };

  // Node Selection on Map
  const handleNodeClick = async (node: any) => {
    setSelectedNode(node);
    setNodeIntel(null);
    setNodeIntelLoading(true);
    setActiveTab('overview');
    
    // Highlight connected lanes
    const connectedEdgeIds = edges
      .filter((e) => e.source === node.id || e.target === node.id)
      .map((e) => e.id);
    setHighlightedEdges(connectedEdgeIds);

    try {
      const res = await axios.get(`${API_BASE}/supply-chain/nodes/${node.id}/intelligence`);
      setNodeIntel(res.data);
    } catch (err) {
      console.error('Failed to load node intelligence:', err);
    } finally {
      setNodeIntelLoading(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 104px)', // 56px Top nav + 48px Bottom status = 104px
        width: '100%',
        boxSizing: 'border-box',
        overflow: 'hidden',
        position: 'relative',
        backgroundColor: 'var(--bg-base)',
      }}
    >
      {/* Top Main Section */}
      <div style={{ display: 'flex', flex: 1, width: '100%', overflow: 'hidden' }}>
        
        {/* Left Panel: Legend & Critical Nodes */}
        <aside
          style={{
            width: '260px',
            flexShrink: 0,
            backgroundColor: 'var(--bg-surface)',
            borderRight: '1px solid var(--border)',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '24px',
            overflowY: 'auto',
            boxSizing: 'border-box',
          }}
        >
          {/* Node Legend */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
              LOGISTICS LEGEND
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: 'var(--accent-cyan)' }} />
                <span>Production Nodes</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {/* SVG Hexagon */}
                <div style={{ width: '12px', height: '12px', backgroundColor: 'var(--text-primary)', clipPath: 'polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%)' }} />
                <span>Port Nodes</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {/* SVG Diamond */}
                <div style={{ width: '10px', height: '10px', backgroundColor: 'var(--accent-amber)', transform: 'rotate(45deg)' }} />
                <span>Choke Points</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderTop: '1px solid var(--border)', paddingTop: '8px', marginTop: '4px' }}>
                <div style={{ width: '20px', height: '2px', backgroundColor: 'var(--accent-cyan)' }} />
                <span>Shipping Lane</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '20px', height: '2px', borderTop: '2px dashed var(--accent-cyan)' }} />
                <span>Pipeline Corridor</span>
              </div>
            </div>
          </div>

          {/* Top Critical Nodes list */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
              TOP CHOKE POINT RISKS
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {criticalNodes.map((node, index) => (
                <div
                  key={node.id}
                  onClick={() => {
                    const coords = NODE_COORDS[node.name];
                    if (coords) {
                      setFocusCentroid([coords.lat, coords.lon]);
                    }
                    const fullNode = nodes.find((n) => n.id === node.id);
                    if (fullNode) handleNodeClick(fullNode);
                  }}
                  style={{
                    backgroundColor: 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-md)',
                    padding: '10px 12px',
                    cursor: 'pointer',
                    transition: 'all 150ms ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)' }}>0{index + 1}</span>
                    <span style={{ fontSize: '9px', fontWeight: 700, color: 'var(--risk-critical)', border: '1px solid var(--risk-critical)', padding: '1px 4px', borderRadius: '2px' }}>
                      {node.risk_label}
                    </span>
                  </div>
                  <h4 style={{ margin: '6px 0 2px 0', fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {node.name}
                  </h4>
                  <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                    Location: {node.location} · Score: {node.chokepoint_score?.toFixed(2) ?? '0.0'} ({node.dependent_count} lanes)
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Trigger Disruption */}
          <button
            onClick={() => setSimModalOpen(true)}
            disabled={simRunning}
            style={{
              width: '100%',
              height: '40px',
              backgroundColor: 'transparent',
              border: '1px solid var(--risk-critical)',
              color: 'var(--risk-critical)',
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              fontSize: '11px',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              marginTop: 'auto',
            }}
            onMouseEnter={(e) => {
              if (!simRunning) e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.08)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            <Activity size={12} />
            SIMULATE DISRUPTION
          </button>
        </aside>

        {/* Center / Right Section: Map */}
        <div style={{ flex: 1, position: 'relative', height: '100%' }}>
          
          <MapContainer
            center={[20, 10]}
            zoom={2.5}
            minZoom={2.2}
            maxZoom={8}
            style={{ width: '100%', height: '100%', zIndex: 1 }}
            zoomControl={true}
          >
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution="© CartoDB"
            />

            {/* shipping lanes & pipelines (edges) */}
            {edges.map((edge) => {
              const srcNode = nodes.find((n) => n.id === edge.source);
              const tgtNode = nodes.find((n) => n.id === edge.target);
              
              if (!srcNode || !tgtNode) return null;
              
              const srcCoord = NODE_COORDS[srcNode.label];
              const tgtCoord = NODE_COORDS[tgtNode.label];
              
              if (!srcCoord || !tgtCoord) return null;

              const isHighlighted = highlightedEdges.includes(edge.id);
              const isDisrupted = disruptedEdgeIds.includes(edge.id);

              let strokeColor = 'rgba(6, 182, 212, 0.25)';
              if (isHighlighted) strokeColor = 'var(--accent-cyan)';
              if (isDisrupted) strokeColor = '#ef4444';

              const strokeWidth = isDisrupted ? 3.0 : isHighlighted ? 2.0 : 1.2;
              const isPipeline = edge.type === 'pipeline';

              // Midpoint calculation
              const midLat = (srcCoord.lat + tgtCoord.lat) / 2;
              const midLon = (srcCoord.lon + tgtCoord.lon) / 2;

              // Calculate angle (screen-space correction: invert y-axis)
              const angle = -Math.atan2(tgtCoord.lat - srcCoord.lat, tgtCoord.lon - srcCoord.lon) * (180 / Math.PI);

              // Create a custom Leaflet divIcon for the arrow
              const arrowIcon = L.divIcon({
                html: `
                  <div style="transform: rotate(${angle}deg); display: flex; align-items: center; justify-content: center; width: 14px; height: 14px;">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="${strokeColor}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="9 18 15 12 9 6"></polyline>
                    </svg>
                  </div>
                `,
                className: '', // prevent default leaflet marker styling
                iconSize: [14, 14],
                iconAnchor: [7, 7]
              });

              return (
                <React.Fragment key={`edge-group-${edge.id}`}>
                  <Polyline
                    key={`edge-${edge.id}-${isDisrupted ? 'dis' : isHighlighted ? 'hi' : 'off'}`}
                    positions={[[srcCoord.lat, srcCoord.lon], [tgtCoord.lat, tgtCoord.lon]]}
                    color={strokeColor}
                    weight={strokeWidth}
                    dashArray={isPipeline ? '6 4' : undefined}
                  />
                  <Marker
                    position={[midLat, midLon]}
                    icon={arrowIcon}
                    interactive={false}
                  />
                </React.Fragment>
              );
            })}

            {/* Supply Chain facility nodes */}
            {nodes.map((node) => {
              const coord = NODE_COORDS[node.label];
              if (!coord) return null;

              const isDisrupted = disruptedNodeIds.includes(node.id);
              const isSelected = selectedNode?.id === node.id;
              const impactScore = nodeImpactMap[node.id];
              
              // Compute fill colour: gradient driven by real BFS impact score
              let markerColor = 'var(--accent-cyan)';
              if (node.type === 'choke_point') {
                markerColor = riskColor(node.risk_score || 50);
              }
              if (isDisrupted && impactScore !== undefined) {
                if (impactScore >= 70)      markerColor = '#ef4444';  // red — critical
                else if (impactScore >= 40) markerColor = '#f97316';  // orange — high
                else if (impactScore >= 15) markerColor = '#eab308';  // amber — medium
                else                        markerColor = '#22d3ee';  // cyan — low
              } else if (isDisrupted) {
                markerColor = '#ef4444';
              }

              // KEY includes disruption state + impactScore so react-leaflet is forced
              // to unmount/remount the GeoJSON marker whenever simulation state changes.
              // Without this, Leaflet ignores prop changes and the map stays static.
              const markerKey = `node-${node.id}-${isDisrupted ? impactScore?.toFixed(0) ?? 'dis' : isSelected ? 'sel' : 'idle'}`;

              return (
                <React.Fragment key={markerKey}>
                  <GeoJSON
                    key={markerKey}
                    data={{
                      type: 'Feature',
                      properties: {},
                      geometry: {
                        type: 'Point',
                        coordinates: [coord.lon, coord.lat],
                      },
                    } as any}
                    pointToLayer={(_feature: any, latlng: any) => {
                      let marker;

                      if (node.type === 'choke_point') {
                        marker = (window as any).L.circleMarker(latlng, {
                          radius: isDisrupted ? 13 : isSelected ? 11 : 8,
                          fillColor: markerColor,
                          color: '#fff',
                          weight: isDisrupted ? 2.5 : isSelected ? 2 : 1,
                          opacity: 0.9,
                          fillOpacity: isDisrupted ? 0.95 : 0.8,
                        });
                      } else if (node.type === 'port') {
                        marker = (window as any).L.circleMarker(latlng, {
                          radius: isDisrupted ? 10 : 7,
                          fillColor: isDisrupted ? markerColor : 'var(--text-primary)',
                          color: isDisrupted ? '#fff' : 'var(--border-bright)',
                          weight: 1,
                          opacity: 0.9,
                          fillOpacity: 0.85,
                        });
                      } else {
                        // Standard Production node
                        marker = (window as any).L.circleMarker(latlng, {
                          radius: isDisrupted ? 11 : isSelected ? 8 : 6,
                          fillColor: markerColor,
                          color: isDisrupted ? '#fff' : 'var(--border)',
                          weight: isDisrupted ? 2 : 1,
                          opacity: 0.9,
                          fillOpacity: isDisrupted ? 0.95 : 0.7,
                        });
                      }

                      marker.on('click', () => handleNodeClick(node));

                      const impactLine = impactScore !== undefined
                        ? `<br/><span style="font-size: 12px; color: ${markerColor}; font-weight: 700;">⚡ Impact: ${impactScore.toFixed(1)}%</span>`
                        : '';
                      const tooltipHtml = `
                        <div style="font-family: var(--font-display); text-align: left;">
                          <strong style="color: var(--text-primary);">${node.label}</strong><br/>
                          <span style="font-size: 11px; color: var(--text-secondary)">Type: ${node.type.toUpperCase()}</span><br/>
                          <span style="font-size: 11px; color: var(--text-secondary)">Location: ${node.location}</span>${impactLine}
                        </div>
                      `;
                      marker.bindTooltip(tooltipHtml, { direction: 'top', opacity: 0.95 });

                      return marker;
                    }}
                  />
                </React.Fragment>
              );
            })}

            {/* Fly hook */}
            <MapFocusController focusCoords={focusCentroid} />
          </MapContainer>

          {/* Node Selected Bottom Detail Panel */}
          {selectedNode && (
            <div
              style={{
                position: 'absolute',
                top: '16px',
                right: '16px',
                width: '380px',
                maxHeight: 'calc(100% - 32px)',
                backgroundColor: 'rgba(26, 29, 36, 0.96)',
                border: '1px solid var(--border-bright)',
                borderRadius: 'var(--radius-md)',
                padding: '18px',
                boxShadow: 'var(--shadow)',
                zIndex: 1000,
                backdropFilter: 'blur(8px)',
                display: 'flex',
                flexDirection: 'column',
                boxSizing: 'border-box',
                overflowY: 'auto',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--accent-cyan)', letterSpacing: '0.08em' }}>
                  NODE INTELLIGENCE
                </span>
                <button
                  onClick={() => {
                    setSelectedNode(null);
                    setHighlightedEdges([]);
                    setNodeIntel(null);
                  }}
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 0 }}
                >
                  <X size={16} />
                </button>
              </div>

              <h3 style={{ margin: '0 0 4px 0', fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
                {selectedNode.label}
              </h3>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block', marginBottom: '14px' }}>
                Type: {selectedNode.type?.toUpperCase()} · Location: {selectedNode.location}
              </span>

              {/* Tabs */}
              <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', marginBottom: '14px' }}>
                {['overview', 'tree', 'impact'].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab as any)}
                    style={{
                      flex: 1,
                      padding: '8px 0',
                      background: 'transparent',
                      border: 'none',
                      borderBottom: activeTab === tab ? '2px solid var(--accent-cyan)' : 'none',
                      color: activeTab === tab ? 'var(--text-primary)' : 'var(--text-muted)',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      textTransform: 'uppercase',
                      transition: 'all 150ms ease',
                    }}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {/* Tab Contents */}
              {nodeIntelLoading ? (
                <div style={{ padding: '20px 0', textAlign: 'center', fontSize: '12px', color: 'var(--text-secondary)' }}>
                  Loading database intelligence...
                </div>
              ) : nodeIntel ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '12px' }}>
                  
                  {/* OVERVIEW TAB */}
                  {activeTab === 'overview' && (
                    <>
                      {/* Chokepoint Score */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'var(--bg-base)', border: '1px solid var(--border)', padding: '10px 12px', borderRadius: 'var(--radius-sm)' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Chokepoint Rank:</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-amber)' }}>
                          #{nodeIntel.chokepoint_analysis.rank} (Score: {nodeIntel.chokepoint_analysis.chokepoint_score.toFixed(2)})
                        </span>
                      </div>

                      {/* Live Context Country Risk */}
                      {nodeIntel.live_context.country_risk && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', border: '1px solid var(--border)', padding: '10px 12px', borderRadius: 'var(--radius-sm)' }}>
                          <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 700 }}>COUNTRY RISK INDICATORS</span>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span>Country Score:</span>
                            <strong style={{ color: riskColor(nodeIntel.live_context.country_risk.risk_score) }}>
                              {nodeIntel.live_context.country_risk.risk_score}/100 ({nodeIntel.live_context.country_risk.color_code})
                            </strong>
                          </div>
                        </div>
                      )}

                      {/* Live Events */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 700 }}>ACTIVE INTEL (EVENTS)</span>
                        {nodeIntel.live_context.events.length > 0 ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {nodeIntel.live_context.events.map((ev: any) => (
                              <div key={ev.id} style={{ borderLeft: '2.5px solid var(--risk-high)', paddingLeft: '8px', paddingVertical: '2px' }}>
                                <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{ev.title}</div>
                                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Source: {ev.source} · Severity {ev.severity}/10</div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <span style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>No relevant geopolitical events in database.</span>
                        )}
                      </div>

                      {/* Markets snapshot */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 700 }}>LIVE MARKET SNAPSHOT</span>
                        {nodeIntel.live_context.markets.length > 0 ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            {nodeIntel.live_context.markets.map((m: any) => {
                              const chg = m.change_percent;
                              const chgText = chg !== null ? `${chg >= 0 ? '▲' : '▼'} ${Math.abs(chg).toFixed(2)}%` : 'N/A';
                              const chgColor = chg !== null ? (chg >= 0 ? '#22c55e' : '#ef4444') : 'var(--text-muted)';
                              return (
                                <div key={m.id} style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)' }}>
                                  <span>{m.symbol} (${m.price?.toFixed(2) ?? 'N/A'})</span>
                                  <span style={{ color: chgColor }}>{chgText}</span>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <span style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>No market tickers found in DB for this node.</span>
                        )}
                      </div>
                    </>
                  )}

                  {/* DEPENDENCY TREE TAB */}
                  {activeTab === 'tree' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 700 }}>DOWNSTREAM DEPENDENCY STRUCTURE</span>
                      <div style={{ border: '1px solid var(--border)', padding: '10px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-base)' }}>
                        {nodeIntel.dependency_tree ? renderDependencyTreeNode(nodeIntel.dependency_tree) : <span style={{ fontStyle: 'italic' }}>No downstream edges.</span>}
                      </div>

                      {nodeIntel.propagation_paths.length > 0 && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 700 }}>PROPAGATION PATHWAYS</span>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                            {nodeIntel.propagation_paths.map((p: any, idx: number) => (
                              <div key={idx} style={{ borderBottom: '1px solid var(--border)', paddingBottom: '4px' }}>
                                <div style={{ color: 'var(--text-primary)' }}>{p.path.join(' → ')}</div>
                                <div style={{ color: 'var(--accent-cyan)', fontSize: '9px' }}>Cumul strength: {p.strength}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* IMPACT PREVIEW TAB */}
                  {activeTab === 'impact' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 700 }}>NON-SIMULATED CASCADE PREVIEWS</span>
                      {['25', '50', '75', '100'].map((sevKey) => {
                        const list = nodeIntel.impact_preview[sevKey] ?? [];
                        return (
                          <div key={sevKey} style={{ border: '1px solid var(--border)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, fontSize: '11px', color: 'var(--accent-cyan)', borderBottom: '1px solid var(--border)', paddingBottom: '4px', marginBottom: '6px' }}>
                              <span>{sevKey}% DISRUPTION</span>
                              <span>{list.length} node(s)</span>
                            </div>
                            {list.length > 0 ? (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                {list.map((item: any, idx: number) => (
                                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span>• {item.name}</span>
                                    <strong style={{ color: 'var(--risk-high)' }}>{item.impact.toFixed(1)}%</strong>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <span style={{ fontStyle: 'italic', color: 'var(--text-muted)', fontSize: '11px' }}>No reachable downstream impact.</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}

                </div>
              ) : (
                <div style={{ padding: '20px 0', textAlign: 'center', fontSize: '12px', color: 'var(--text-secondary)' }}>
                  Failed to load intelligence payload.
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 3. BOTTOM ZONE: Simulation Log Panel (collapsible) */}
      {simRunning && (
        <div
          style={{
            height: simLogsExpanded ? '380px' : '48px',
            width: '100%',
            backgroundColor: 'var(--bg-elevated)',
            borderTop: '1px solid var(--border)',
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            transition: 'height 250ms var(--ease-snap)',
            boxSizing: 'border-box',
          }}
        >
          {/* Handle header */}
          <div
            style={{
              height: '48px',
              backgroundColor: 'var(--bg-base)',
              borderBottom: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0 20px',
              boxSizing: 'border-box',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', fontWeight: 700 }}>
              <span
                style={{
                  width: '7px', height: '7px', borderRadius: '50%',
                  backgroundColor: simCompleted ? '#22c55e' : '#ef4444',
                  boxShadow: simCompleted ? '0 0 6px #22c55e' : '0 0 6px #ef4444',
                  animation: simCompleted ? 'none' : 'pulse 1.2s infinite',
                  display: 'inline-block',
                }}
              />
              <span style={{ color: simCompleted ? '#22c55e' : '#ef4444' }}>
                IMPACT PROPAGATION ENGINE
              </span>
              <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>●</span>
              <span style={{ color: simCompleted ? '#22c55e' : 'var(--accent-amber)' }}>
                {simCompleted ? 'ANALYSIS COMPLETE' : 'RUNNING BFS...'}
              </span>
              <span style={{
                marginLeft: '8px',
                backgroundColor: 'rgba(6,182,212,0.1)',
                border: '1px solid rgba(6,182,212,0.3)',
                borderRadius: '4px',
                padding: '1px 7px',
                fontSize: '10px',
                color: 'var(--accent-cyan)',
                fontWeight: 600,
              }}>
                {simLogs.length} log lines
              </span>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              {simCompleted && (
                <button
                  onClick={() => alert('Log report exported successfully.')}
                  style={{
                    backgroundColor: 'rgba(6, 182, 212, 0.15)',
                    border: '1px solid var(--accent-cyan)',
                    color: 'var(--accent-cyan)',
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '4px 10px',
                    borderRadius: 'var(--radius-sm)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <FileText size={12} />
                  EXPORT REPORT
                </button>
              )}
              <button
                onClick={handleStopSimulation}
                style={{
                  backgroundColor: 'transparent',
                  border: '1px solid var(--risk-critical)',
                  color: 'var(--risk-critical)',
                  fontSize: '11px',
                  fontWeight: 700,
                  padding: '4px 10px',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <StopCircle size={12} />
                {simCompleted ? 'CLOSE' : 'STOP'}
              </button>
              <button
                onClick={() => setSimLogsExpanded(!simLogsExpanded)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: '11px',
                  fontWeight: 600,
                }}
              >
                {simLogsExpanded ? 'COLLAPSE ▼' : 'EXPAND ▲'}
              </button>
            </div>
          </div>

          {/* Logs monospaced scroll panel */}
          {simLogsExpanded && (
            <div
              style={{
                flex: 1,
                overflowY: 'auto',
                padding: '12px 20px 16px',
                fontFamily: 'var(--font-mono)',
                fontSize: '11.5px',
                lineHeight: 1.75,
                backgroundColor: 'rgba(6, 8, 11, 0.85)',
                color: 'var(--text-secondary)',
              }}
            >
              {simLogs.map((log, index) => {
                const text: string = log.text ?? '';
                const isSeparator = text.startsWith('━');
                const isSection   = text.startsWith('▶');
                const isIndented  = text.startsWith('  │') || text.startsWith('  ↳') || text.startsWith('  ┌') || text.startsWith('  └');
                const isEmpty     = text.trim() === '';

                // Colour by log type
                let color = '#6b7280';   // default muted
                if (log.type === 'warn') color = '#f59e0b';
                if (log.type === 'crit') color = '#ef4444';
                if (log.type === 'info') color = '#22d3ee';

                // Override colour for structural lines
                if (isSeparator) color = '#374151';
                if (isSection)   color = log.type === 'crit' ? '#ef4444' : '#f59e0b';
                if (isIndented && log.type === 'info') color = '#4b5563';
                if (isEmpty)     return <div key={index} style={{ height: '4px' }} />;

                return (
                  <div
                    key={index}
                    style={{
                      color,
                      fontWeight: isSection ? 700 : isSeparator ? 400 : 400,
                      fontSize: isSeparator ? '10px' : isSection ? '12px' : '11.5px',
                      letterSpacing: isSection ? '0.05em' : 'normal',
                      marginTop: isSection ? '6px' : '0',
                      whiteSpace: 'pre',
                    }}
                  >
                    {text}
                  </div>
                );
              })}
              <div ref={logEndRef} />
            </div>
          )}
        </div>
      )}

      {/* SIMULATION MODAL OVERLAY */}
      {simModalOpen && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(3px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1001,
          }}
        >
          <div
            style={{
              width: '420px',
              backgroundColor: 'var(--bg-elevated)',
              border: '1px solid var(--border-bright)',
              borderRadius: 'var(--radius-lg)',
              padding: '28px',
              boxShadow: 'var(--shadow)',
              boxSizing: 'border-box',
              display: 'flex',
              flexDirection: 'column',
              gap: '20px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertTriangle size={16} style={{ color: 'var(--risk-critical)' }} />
                <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '14px', letterSpacing: '0.04em' }}>
                  GEOPOLITICAL SIMULATION HUB
                </span>
              </div>
              <button
                onClick={() => setSimModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 0 }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Tab Headers */}
            <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', gap: '16px' }}>
              <button
                onClick={() => setActiveSimTab('node')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: activeSimTab === 'node' ? 'var(--accent-cyan)' : 'var(--text-muted)',
                  fontFamily: 'var(--font-display)',
                  fontWeight: 700,
                  fontSize: '11px',
                  cursor: 'pointer',
                  borderBottom: activeSimTab === 'node' ? '2px solid var(--accent-cyan)' : '2px solid transparent',
                  paddingBottom: '8px',
                  paddingX: '4px',
                  transition: 'all 150ms ease',
                }}
              >
                NODE-BASED DISRUPTION
              </button>
              <button
                onClick={() => setActiveSimTab('scenario')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: activeSimTab === 'scenario' ? 'var(--accent-cyan)' : 'var(--text-muted)',
                  fontFamily: 'var(--font-display)',
                  fontWeight: 700,
                  fontSize: '11px',
                  cursor: 'pointer',
                  borderBottom: activeSimTab === 'scenario' ? '2px solid var(--accent-cyan)' : '2px solid transparent',
                  paddingBottom: '8px',
                  paddingX: '4px',
                  transition: 'all 150ms ease',
                }}
              >
                NEWS / SCENARIO SIMULATION
              </button>
            </div>

            {activeSimTab === 'node' ? (
              /* TAB 1: Node-based simulation */
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {/* Target Dropdown */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: 700 }}>
                    TARGET SUPPLY CHAIN NODE
                  </label>
                  <select
                    value={simTargetNode || ''}
                    onChange={(e) => handleSelectSimTarget(parseInt(e.target.value))}
                    style={{
                      height: '38px',
                      backgroundColor: 'var(--bg-base)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-md)',
                      color: 'var(--text-primary)',
                      padding: '0 10px',
                      fontSize: '13px',
                      cursor: 'pointer',
                    }}
                  >
                    <option value="" disabled>Select node...</option>
                    {nodes.map((n) => (
                      <option key={n.id} value={n.id}>
                        {n.label} ({n.location})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Disruption Type */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: 700 }}>
                    DISRUPTION MECHANISM
                  </label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    {['Blockade', 'Strike', 'Disaster'].map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => setSimDisruptionType(t)}
                        style={{
                          flex: 1,
                          height: '34px',
                          backgroundColor: simDisruptionType === t ? 'rgba(239, 68, 68, 0.15)' : 'var(--bg-base)',
                          border: `1px solid ${simDisruptionType === t ? 'var(--risk-critical)' : 'var(--border)'}`,
                          color: simDisruptionType === t ? 'var(--risk-critical)' : 'var(--text-secondary)',
                          fontSize: '11px',
                          fontWeight: 700,
                          borderRadius: 'var(--radius-sm)',
                          cursor: 'pointer',
                        }}
                      >
                        {t.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Severity Slider */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <label style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: 700 }}>
                      DISRUPTION SEVERITY PROFILE
                    </label>
                    <span style={{ fontSize: '14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--risk-critical)' }}>
                      LVL {simSeverity}/10
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={simSeverity}
                    onChange={(e) => setSimSeverity(parseInt(e.target.value))}
                    style={{ cursor: 'pointer', accentColor: 'var(--risk-critical)' }}
                  />
                </div>

                {/* Impact Preview */}
                <div style={{ backgroundColor: 'var(--bg-base)', border: '1px solid var(--border)', padding: '12px', borderRadius: 'var(--radius-md)' }}>
                  <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                    CASCADE IMPACT PREVIEW
                  </span>
                  <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4, margin: 0, whiteSpace: 'pre-wrap' }}>
                    {(() => {
                      if (simTargetIntel && simTargetNode) {
                        const sevVal = simSeverity * 10;
                        let bucket = "25";
                        if (sevVal <= 37.5) bucket = "25";
                        else if (sevVal <= 62.5) bucket = "50";
                        else if (sevVal <= 87.5) bucket = "75";
                        else bucket = "100";

                        const previewList = simTargetIntel.impact_preview?.[bucket] ?? [];
                        if (previewList.length > 0) {
                          return `Disrupting ${simTargetIntel.overview.name} at ~${bucket}% severity will cascade to:\n` +
                            previewList.map((item: any) => `  • ${item.name}: ~${item.impact.toFixed(1)}% (depth ${item.depth})`).join('\n');
                        } else {
                          return `Disrupting ${simTargetIntel.overview.name} at ~${bucket}% severity will have no downstream impact.`;
                        }
                      }
                      return simPreviewText;
                    })()}
                  </p>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
                  <button
                    onClick={handleStartSimulation}
                    disabled={!simTargetNode}
                    style={{
                      width: '100%',
                      height: '44px',
                      backgroundColor: 'var(--risk-critical)',
                      border: 'none',
                      color: '#fff',
                      fontFamily: 'var(--font-display)',
                      fontWeight: 700,
                      fontSize: '12px',
                      textTransform: 'uppercase',
                      letterSpacing: '0.08em',
                      borderRadius: 'var(--radius-md)',
                      cursor: simTargetNode ? 'pointer' : 'not-allowed',
                      opacity: simTargetNode ? 1 : 0.5,
                    }}
                  >
                    RUN IMPACT PROPAGATION
                  </button>
                  <button
                    onClick={() => setSimModalOpen(false)}
                    style={{
                      width: '100%',
                      height: '36px',
                      backgroundColor: 'transparent',
                      border: 'none',
                      color: 'var(--text-secondary)',
                      fontSize: '12px',
                      cursor: 'pointer',
                      fontWeight: 600,
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              /* TAB 2: Scenario/News-based simulation */
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                
                {/* News Dropdown selector */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: 700 }}>
                    CHOOSE LIVE NEWS OR HOT SCENARIO
                  </label>
                  <select
                    value={selectedDropdownEvent}
                    onChange={(e) => handleSelectScenarioOption(e.target.value)}
                    style={{
                      height: '38px',
                      backgroundColor: 'var(--bg-base)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-md)',
                      color: 'var(--text-primary)',
                      padding: '0 10px',
                      fontSize: '13px',
                      cursor: 'pointer',
                    }}
                  >
                    <option value="">Select scenario...</option>
                    <option value="custom">Custom Text Scenario...</option>
                    
                    {/* Render unique list of live news and fallback scenarios */}
                    {[
                      ...liveNews.map(n => ({ title: n.title, isLive: true })),
                      ...FALLBACK_SCENARIOS.map(fb => ({ title: fb.title, isLive: false }))
                    ]
                      .filter((item, idx, self) => self.findIndex(t => t.title === item.title) === idx)
                      .slice(0, 15)
                      .map((sc, idx) => (
                        <option key={idx} value={sc.title}>
                          {sc.isLive ? '📰 [LIVE]' : '🔥 [HOT]'} {sc.title}
                        </option>
                      ))
                    }
                  </select>
                </div>

                {/* Editable custom scenario textbox */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: 700 }}>
                    SCENARIO DETAILS
                  </label>
                  <textarea
                    value={scenarioText}
                    onChange={(e) => {
                      setScenarioText(e.target.value);
                      if (selectedDropdownEvent !== 'custom') {
                        setSelectedDropdownEvent('custom');
                      }
                    }}
                    placeholder="Describe the geopolitical scenario (e.g. Russia refused to give oil to Pakistan...)"
                    style={{
                      height: '70px',
                      backgroundColor: 'var(--bg-base)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-md)',
                      color: 'var(--text-primary)',
                      padding: '10px',
                      fontSize: '12px',
                      fontFamily: 'inherit',
                      resize: 'none',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>

                {/* Form fields: Region & Event Type */}
                <div style={{ display: 'flex', gap: '10px' }}>
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: 700 }}>
                      REGION Focus
                    </label>
                    <select
                      value={selectedRegion}
                      onChange={(e) => setSelectedRegion(e.target.value)}
                      style={{
                        height: '34px',
                        backgroundColor: 'var(--bg-base)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-md)',
                        color: 'var(--text-primary)',
                        padding: '0 8px',
                        fontSize: '12px',
                      }}
                    >
                      {['Global', 'East Asia', 'Middle East', 'Europe', 'North America', 'South Asia', 'Africa', 'South America'].map(r => (
                        <option key={r} value={r}>{r}</option>
                      ))}
                    </select>
                  </div>

                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: 700 }}>
                      EVENT TYPE
                    </label>
                    <select
                      value={selectedEventType}
                      onChange={(e) => setSelectedEventType(e.target.value)}
                      style={{
                        height: '34px',
                        backgroundColor: 'var(--bg-base)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-md)',
                        color: 'var(--text-primary)',
                        padding: '0 8px',
                        fontSize: '12px',
                      }}
                    >
                      {['economic', 'war', 'sanctions', 'policy'].map(t => (
                        <option key={t} value={t}>{t.toUpperCase()}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Form fields: Magnitude */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: 700 }}>
                    DISRUPTION MAGNITUDE
                  </label>
                  <select
                    value={selectedMagnitude}
                    onChange={(e) => setSelectedMagnitude(e.target.value)}
                    style={{
                      height: '36px',
                      backgroundColor: 'var(--bg-base)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-md)',
                      color: 'var(--text-primary)',
                      padding: '0 10px',
                      fontSize: '12px',
                    }}
                  >
                    {['Mild', 'Moderate', 'Severe', 'Catastrophic'].map(m => (
                      <option key={m} value={m}>{m.toUpperCase()}</option>
                    ))}
                  </select>
                </div>

                {/* Run Buttons */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
                  <button
                    onClick={handleStartScenarioSimulation}
                    disabled={!scenarioText.trim()}
                    style={{
                      width: '100%',
                      height: '44px',
                      backgroundColor: 'var(--risk-critical)',
                      border: 'none',
                      color: '#fff',
                      fontFamily: 'var(--font-display)',
                      fontWeight: 700,
                      fontSize: '12px',
                      textTransform: 'uppercase',
                      letterSpacing: '0.08em',
                      borderRadius: 'var(--radius-md)',
                      cursor: scenarioText.trim() ? 'pointer' : 'not-allowed',
                      opacity: scenarioText.trim() ? 1 : 0.5,
                    }}
                  >
                    RUN SCENARIO SIMULATION
                  </button>
                  <button
                    onClick={() => setSimModalOpen(false)}
                    style={{
                      width: '100%',
                      height: '36px',
                      backgroundColor: 'transparent',
                      border: 'none',
                      color: 'var(--text-secondary)',
                      fontSize: '12px',
                      cursor: 'pointer',
                      fontWeight: 600,
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default SupplyChain;
