import logging
import random
from collections import deque
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional, Dict, Any
from ..repositories.supply_chain_repo import SupplyChainRepository
from ..repositories.event_repo import EventRepository
from ..repositories.market_repo import MarketRepository
from ..repositories.risk_repo import CountryRiskRepository, GTIRepository
from ..schemas.supply_chain_schema import (
    SupplyChainNodeCreate,
    SupplyChainDependencyCreate,
    SimulateRequest,
    SimulateResponse,
    AffectedNodeResult,
    SimulationLog,
    DependencyTreeNode,
    ImpactPreviewItem,
    PropagationPathItem,
    ChokepointAnalysisResult,
    NodeOverview,
    NodeLiveContext,
    NodeIntelligenceResponse,
)
from ..models.supply_chain_model import SupplyChainNode, SupplyChainDependency
from ..models.event_model import Event
from ..models.market_model import Market
from ..models.country_risk_model import CountryRisk

logger = logging.getLogger("geotrade.services.supply_chain")

_VARIABILITY_BAND = 0.05
_MIN_IMPACT_THRESHOLD = 1.0

# ── Node → country name keywords (used to text-search events) ────────────────
_NODE_LOCATION_KEYWORDS: Dict[str, List[str]] = {
    "Semiconductors":            ["taiwan", "tsmc", "semiconductor", "chip"],
    "Rare Earth Minerals":       ["china", "rare earth", "mineral", "lithium"],
    "Crude Oil":                 ["saudi", "opec", "oil", "crude", "petroleum"],
    "Natural Gas":               ["russia", "gas", "lng", "pipeline", "gazprom"],
    "Agriculture / Grain":       ["ukraine", "grain", "wheat", "food", "harvest", "agriculture"],
    "Tech Industry":             ["tech", "silicon", "nasdaq", "ai", "software"],
    "Electronics Manufacturing": ["china", "electronics", "manufacturing", "shenzhen", "factory"],
    "Energy Sector":             ["energy", "power", "grid", "electricity", "fuel"],
    "Automotive Industry":       ["auto", "vehicle", "car", "ev", "germany"],
    "Defense Sector":            ["defense", "military", "weapons", "nato", "pentagon"],
    "Advanced Lithography (EUV)":["netherlands", "asml", "lithography", "euv"],
    "Lithium / Battery Cells":   ["australia", "lithium", "battery", "ev", "albemarle"],
    "Cobalt Mining":             ["congo", "cobalt", "glencore", "mining"],
    "Suez Canal Transit":        ["egypt", "suez", "canal", "transit", "shipping"],
    "Strait of Malacca Transit": ["singapore", "malacca", "strait", "shipping", "transit"],
    "Potash / Fertilizers":      ["canada", "potash", "fertilizer", "nutrient"],
}

# ── Node → market ticker keywords (matched against Market.symbol or Market.name) ─
_NODE_TICKER_KEYWORDS: Dict[str, List[str]] = {
    "Semiconductors":            ["TSM", "NVDA", "INTC", "AMD", "SOXX"],
    "Rare Earth Minerals":       ["MP", "MPNGF", "LYNAS"],
    "Crude Oil":                 ["XOM", "CVX", "COP", "BP", "USO"],
    "Natural Gas":               ["LNG", "CQP", "UNG"],
    "Tech Industry":             ["QQQ", "AAPL", "MSFT", "GOOGL"],
    "Electronics Manufacturing": ["HON", "EMR", "ABB"],
    "Energy Sector":             ["XLE", "VDE", "SHEL", "TTE"],
    "Automotive Industry":       ["TM", "F", "GM", "STLA", "RACE"],
    "Defense Sector":            ["LMT", "RTX", "BA", "NOC", "GD"],
    "Agriculture / Grain":       ["ADM", "BG", "CTVA", "MOS"],
    "Advanced Lithography (EUV)":["ASML"],
    "Lithium / Battery Cells":   ["ALB", "LTHM", "LAC"],
    "Cobalt Mining":             ["GLCNF", "GLNCY"],
    "Suez Canal Transit":        ["EGPT"],
    "Strait of Malacca Transit": ["EWS"],
    "Potash / Fertilizers":      ["NTR", "MOS"],
}

_IMPACT_LABEL_COLOR: Dict[str, str] = {
    "CRITICAL": "crit",
    "HIGH":     "warn",
    "MEDIUM":   "info",
    "LOW":      "info",
}

def _risk_label(impact: float) -> str:
    if impact >= 70: return "CRITICAL"
    if impact >= 40: return "HIGH"
    if impact >= 15: return "MEDIUM"
    return "LOW"

def _risk_type(impact: float) -> str:
    return _IMPACT_LABEL_COLOR[_risk_label(impact)]

_DISRUPTION_CONTEXT: Dict[str, Dict] = {
    "Blockade": {
        "verb":      "blockaded",
        "immediate": "All inbound/outbound freight halted. Port access denied. Logistics networks forced to reroute.",
        "financial": "Spot prices expected to spike 15–40% within 48h. Futures markets moving into contango.",
    },
    "Strike": {
        "verb":      "hit by industrial action",
        "immediate": "Production halted by labour stoppage. Inventory drawdown begins immediately.",
        "financial": "Typical inventory buffer of 2–4 weeks. Futures contracts under renegotiation pressure.",
    },
    "Disaster": {
        "verb":      "struck by catastrophic event",
        "immediate": "Physical infrastructure compromised. Emergency logistics and insurance protocols activated.",
        "financial": "Force majeure clauses invoked on active contracts. Insurance triggers expected.",
    },
}


# ── Live context loader ───────────────────────────────────────────────────────

def _build_live_context(db: Session, node_name: str) -> Dict[str, Any]:
    """
    Queries the live database to build node-specific context:
    - Recent geopolitical events matching the node's location/sector keywords
    - Market assets related to the node's sector (with live price + change)
    - Current GTI score
    - Country risk data (if available)

    Returns a dict safe to use inside log generation.
    All queries are best-effort — failures return empty lists/None gracefully.
    """
    ctx: Dict[str, Any] = {
        "events":       [],
        "markets":      [],
        "gti_score":    None,
        "gti_label":    None,
        "country_risk": None,
    }

    keywords = _NODE_LOCATION_KEYWORDS.get(node_name, [])
    ticker_kws = _NODE_TICKER_KEYWORDS.get(node_name, [])

    # ── 1. Recent events matching node keywords ───────────────────────────────
    try:
        event_repo = EventRepository(db)
        all_events: List[Event] = event_repo.get_all(limit=200)
        matched = []
        for ev in all_events:
            text = f"{ev.title} {ev.description or ''}".lower()
            if any(kw in text for kw in keywords):
                matched.append(ev)
        # Sort by severity desc, take top 3
        matched.sort(key=lambda e: (e.severity or 0), reverse=True)
        ctx["events"] = matched[:3]
    except Exception as e:
        logger.debug("Live context: event query failed for %s: %s", node_name, e)

    # ── 2. Market assets matching node tickers ────────────────────────────────
    try:
        market_repo = MarketRepository(db)
        all_markets: List[Market] = market_repo.get_all()
        matched_mkts = []
        for m in all_markets:
            sym = (m.symbol or "").upper()
            if sym in [t.upper() for t in ticker_kws]:
                m.change_percent = 0.0
                if m.price:
                    hist = market_repo.get_history(m.id, limit=2)
                    if hist:
                        baseline = hist[0].close
                        if len(hist) > 1 and abs(m.price - baseline) < 0.01:
                            baseline = hist[1].close
                        if baseline:
                            m.change_percent = ((m.price - baseline) / baseline) * 100
                matched_mkts.append(m)
        ctx["markets"] = matched_mkts[:4]
    except Exception as e:
        logger.debug("Live context: market query failed for %s: %s", node_name, e)

    # ── 3. GTI score ──────────────────────────────────────────────────────────
    try:
        gti_repo = GTIRepository(db)
        gti = gti_repo.get_latest()
        if gti:
            ctx["gti_score"] = round(gti.score, 1) if gti.score else None
            ctx["gti_label"] = gti.risk_level if hasattr(gti, "risk_level") else None
    except Exception as e:
        logger.debug("Live context: GTI query failed: %s", e)

    # ── 4. Country risk ────────────────────────────────────────────────────────
    try:
        risk_repo = CountryRiskRepository(db)
        # Try to find a country risk record matching the node's location keywords
        all_risks: List[CountryRisk] = risk_repo.get_all()
        for risk in all_risks:
            country_name = (risk.country_name or risk.country_code or "").lower()
            if any(kw in country_name for kw in keywords):
                ctx["country_risk"] = risk
                break
    except Exception as e:
        logger.debug("Live context: country risk query failed for %s: %s", node_name, e)

    return ctx


def _fmt_market(m: Market) -> str:
    """Format a single market asset into a compact log line."""
    sym    = m.symbol or "???"
    name   = (m.name or "")[:28]
    price  = f"${m.price:.2f}" if m.price else "N/A"
    chg    = getattr(m, "change_percent", None)
    if chg is not None:
        arrow = "▲" if chg >= 0 else "▼"
        chg_s = f"{arrow} {abs(chg):.2f}%"
    else:
        chg_s = "N/A"
    geo    = f"  geo-sens {m.geo_sensitivity:.2f}" if m.geo_sensitivity else ""
    return f"{sym:<6} {price:<10} {chg_s:<12} {name}{geo}"


def _fmt_event(ev: Event) -> str:
    """Format a geopolitical event into a single summary line."""
    title   = (ev.title or "Unknown event")[:80]
    sev     = ev.severity or 0
    etype   = (ev.event_type or "event").upper()
    source  = ev.source or ""
    return f"[{etype}] Sev {sev}/10 — {title}  ({source})"


class SupplyChainService:

    # ── Node operations ──────────────────────────────────────────────────────

    def get_all_nodes(self, db: Session) -> List[SupplyChainNode]:
        return SupplyChainRepository(db).get_all_nodes()

    def get_node(self, db: Session, node_id: int) -> Optional[SupplyChainNode]:
        return SupplyChainRepository(db).get_node_by_id(node_id)

    def get_nodes_by_location(self, db: Session, location: str) -> List[SupplyChainNode]:
        return SupplyChainRepository(db).get_nodes_by_location(location)

    def create_node(self, db: Session, node_in: SupplyChainNodeCreate) -> SupplyChainNode:
        return SupplyChainRepository(db).create_node(node_in)

    # ── Dependency operations ────────────────────────────────────────────────

    def get_dependencies(self, db: Session, node_id: int) -> List[SupplyChainDependency]:
        return SupplyChainRepository(db).get_dependencies_for_node(node_id)

    def get_dependents(self, db: Session, node_id: int) -> List[SupplyChainDependency]:
        return SupplyChainRepository(db).get_dependents_of_node(node_id)

    def create_dependency(self, db: Session, dep_in: SupplyChainDependencyCreate) -> SupplyChainDependency:
        return SupplyChainRepository(db).create_dependency(dep_in)

    # ── Analytics ───────────────────────────────────────────────────────────

    def get_risk_graph(self, db: Session, location=None, node_type=None,
                       min_strength=None, dependency_type=None) -> dict:
        repo  = SupplyChainRepository(db)
        nodes = repo.get_all_nodes()
        edges = repo.get_all_dependencies()

        filtered_nodes = [
            n for n in nodes
            if (not location or location.lower() in n.location.lower())
            and (not node_type or node_type.lower() == n.type.lower())
        ]
        ids = {n.id for n in filtered_nodes}

        filtered_edges = [
            e for e in edges
            if (min_strength is None or e.dependency_strength >= min_strength)
            and (not dependency_type or dependency_type.lower() == e.dependency_type.lower())
            and e.source_node_id in ids and e.target_node_id in ids
        ]

        return {
            "nodes": [{"id": n.id, "label": n.name, "location": n.location, "type": n.type}
                      for n in filtered_nodes],
            "edges": [{"id": e.id, "source": e.source_node_id, "target": e.target_node_id,
                       "type": e.dependency_type, "strength": e.dependency_strength}
                      for e in filtered_edges],
        }

    def get_critical_nodes(self, db: Session, min_score: float = 0.5) -> List[dict]:
        repo = SupplyChainRepository(db)
        nodes = repo.get_all_nodes()
        adjacency = repo.get_adjacency_map()

        critical = []
        for n in nodes:
            deps = adjacency.get(n.id, [])
            score = sum(dep.dependency_strength or 0.0 for dep in deps)
            if score >= min_score:
                critical.append({
                    "id": n.id,
                    "name": n.name,
                    "location": n.location,
                    "type": n.type,
                    "chokepoint_score": round(score, 4),
                    "dependent_count": len(deps),
                    "risk_label": "CRITICAL" if score >= 1.5 else "HIGH"
                })
        return sorted(critical, key=lambda x: x["chokepoint_score"], reverse=True)

    # ── BFS Impact Propagation Simulation ───────────────────────────────────

    def run_supply_chain_simulation(
        self, db: Session, request: SimulateRequest
    ) -> SimulateResponse:
        """
        Runs a real BFS impact propagation simulation with live-data-enriched logs.

        Context pulled at simulation time from live DB:
          • Geopolitical events matching the node's location/sector keywords
          • Live market prices for sector-linked tickers
          • Current GTI score
          • Country risk scores for the node's location
        """
        repo = SupplyChainRepository(db)

        nodes_map = repo.get_all_nodes_map()
        adjacency = repo.get_adjacency_map()

        source_node = nodes_map.get(request.node_id)
        if source_node is None:
            raise ValueError(f"Node with id={request.node_id} not found.")

        severity = float(max(0.0, min(100.0, request.severity)))
        d_ctx    = _DISRUPTION_CONTEXT.get(request.disruption_type, _DISRUPTION_CONTEXT["Blockade"])
        risk_lbl = _risk_label(severity)

        # ── Load live context (all DB, never external API) ────────────────────
        live = _build_live_context(db, source_node.name)
        gti_str = f"{live['gti_score']}" if live['gti_score'] else "N/A"

        logs: List[SimulationLog]           = []
        affected_nodes: List[AffectedNodeResult] = []
        step = 0

        def add(text: str, t: str = "info") -> None:
            nonlocal step
            step += 1
            logs.append(SimulationLog(step=step, text=text, type=t))

        # ══════════════════════════════════════════════════════════════════════
        #  SECTION 1 — Disruption Declaration
        # ══════════════════════════════════════════════════════════════════════
        add("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info")
        add("⚡ DISRUPTION EVENT DECLARED", "crit")
        add(f"   Node       : {source_node.name}", "crit")
        add(f"   Location   : {source_node.location}", "crit")
        add(f"   Mechanism  : {request.disruption_type.upper()} — {source_node.name} {d_ctx['verb']}", "crit")
        add(f"   Severity   : {severity:.0f}%  [ {risk_lbl} ]",
            "crit" if severity >= 70 else "warn")
        add(f"   Global GTI : {gti_str}  (current geopolitical tension index)", "info")
        add(f"   Variability: {'ON — ±5% stochastic noise applied per hop' if request.apply_variability else 'OFF — deterministic run'}", "info")
        add("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info")

        # ══════════════════════════════════════════════════════════════════════
        #  SECTION 2 — Live Geopolitical Context for Source Node
        # ══════════════════════════════════════════════════════════════════════
        add("", "info")
        add(f"▶ LIVE GEOPOLITICAL CONTEXT: {source_node.name.upper()}", "crit" if severity >= 70 else "warn")
        add(f"  ↳ Immediate effect : {d_ctx['immediate']}", "warn")
        add(f"  ↳ Financial signal : {d_ctx['financial']}", "warn")

        if live["events"]:
            add(f"  ↳ Active intel ({len(live['events'])} recent event(s) matching this node):", "warn")
            for ev in live["events"]:
                add(f"     • {_fmt_event(ev)}", "crit" if (ev.severity or 0) >= 7 else "warn")
        else:
            add(f"  ↳ No matching geopolitical events in DB for this node/location.", "info")

        if live["country_risk"]:
            cr = live["country_risk"]
            add(f"  ↳ Country risk ({cr.country_code}): "
                f"Risk {cr.risk_score:.0f}/100 | "
                f"Political stability {getattr(cr, 'political_stability', 'N/A')} | "
                f"Economic stability {getattr(cr, 'economic_stability', 'N/A')}", "warn")

        # ── Live market ticker snapshot ────────────────────────────────────────
        if live["markets"]:
            add("", "info")
            add(f"  ↳ LIVE MARKET SNAPSHOT — {source_node.name} sector tickers:", "warn")
            add(f"     {'SYMBOL':<7} {'PRICE':<11} {'CHANGE':<13} NAME / SENSITIVITY", "info")
            add(f"     {'─'*60}", "info")
            for m in live["markets"]:
                add(f"     {_fmt_market(m)}", "info")
        else:
            add(f"  ↳ No sector market data found in DB for this node.", "info")

        # ══════════════════════════════════════════════════════════════════════
        #  SECTION 3 — BFS Propagation
        # ══════════════════════════════════════════════════════════════════════
        add("", "info")
        add("▶ RUNNING BFS IMPACT PROPAGATION ENGINE...", "info")
        outgoing_count = len(adjacency.get(source_node.id, []))
        add(f"  ↳ {outgoing_count} direct downstream dependency link(s) registered for this node", "info")

        queue: deque = deque()
        queue.append((source_node.id, severity, 0, 1.0))
        visited: set = {source_node.id}
        depth_groups: Dict[int, List[AffectedNodeResult]] = {}

        while queue:
            node_id, parent_impact, depth, edge_strength = queue.popleft()
            node = nodes_map.get(node_id)
            if node is None:
                continue

            if depth > 0:
                result = AffectedNodeResult(
                    node_id=node_id,
                    name=node.name,
                    location=node.location,
                    node_type=node.type or "unknown",
                    impact=round(parent_impact, 2),
                    depth=depth,
                    dependency_strength=round(edge_strength, 4),
                )
                affected_nodes.append(result)
                depth_groups.setdefault(depth, []).append(result)

            for dep in adjacency.get(node_id, []):
                child_id = dep.target_node_id
                if child_id in visited:
                    continue
                strength     = dep.dependency_strength or 0.5
                child_impact = parent_impact * strength
                if request.apply_variability:
                    child_impact *= 1.0 + random.uniform(-_VARIABILITY_BAND, _VARIABILITY_BAND)
                child_impact = max(0.0, min(100.0, child_impact))

                if child_impact < _MIN_IMPACT_THRESHOLD:
                    child_node = nodes_map.get(child_id)
                    child_name = child_node.name if child_node else f"Node #{child_id}"
                    add(f"  ↳ {child_name} — impact {child_impact:.1f}% below threshold, branch pruned.", "info")
                    continue
                visited.add(child_id)
                queue.append((child_id, child_impact, depth + 1, strength))

        # ══════════════════════════════════════════════════════════════════════
        #  SECTION 4 — Per-depth Impact Report (with live market data per node)
        # ══════════════════════════════════════════════════════════════════════
        if affected_nodes:
            add("", "info")
            add("▶ CASCADE IMPACT REPORT", "warn")

            for depth_lvl in sorted(depth_groups.keys()):
                add("", "info")
                add(f"  ┌─ PROPAGATION DEPTH {depth_lvl} ─────────────────────────────────────────", "warn")
                for n in depth_groups[depth_lvl]:
                    rl = _risk_label(n.impact)
                    rt = _risk_type(n.impact)

                    add(f"  │  ⬤ {n.name}  ({n.location})  [{rl}]", rt)
                    add(f"  │    Impact score    : {n.impact:.1f}%", rt)
                    add(f"  │    Edge strength   : {n.dependency_strength:.0%}  "
                        f"({severity:.0f}% source × {n.dependency_strength:.0%} = {n.impact:.1f}%)", "info")

                    # Live events for this downstream node
                    child_live = _build_live_context(db, n.name)
                    if child_live["events"]:
                        add(f"  │    Active intel    : {len(child_live['events'])} matching event(s)", rt)
                        for ev in child_live["events"][:2]:
                            add(f"  │      • {_fmt_event(ev)}", "crit" if (ev.severity or 0) >= 7 else "warn")

                    # Live market tickers for this node
                    if child_live["markets"]:
                        add(f"  │    Market snapshot :", "info")
                        for m in child_live["markets"][:3]:
                            add(f"  │      {_fmt_market(m)}", "info")
                    else:
                        add(f"  │    Market data     : No matching tickers in DB", "info")

                    add("  │", "info")
                add("  └──────────────────────────────────────────────────────────────────", "warn")
        else:
            add("", "info")
            add(f"  ↳ No downstream nodes reachable from {source_node.name} in current graph.", "info")
            add(f"  ↳ Disruption is localised to {source_node.location}.", "warn")
            add(f"  ↳ Monitor for escalation — geopolitical events can alter propagation scope.", "warn")

        # ══════════════════════════════════════════════════════════════════════
        #  SECTION 5 — Executive Summary
        # ══════════════════════════════════════════════════════════════════════
        max_depth   = max((n.depth for n in affected_nodes), default=0)
        highest     = max(affected_nodes, key=lambda n: n.impact, default=None)
        total_nodes = len(affected_nodes)

        add("", "info")
        add("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info")
        add("▶ EXECUTIVE SUMMARY", "warn")
        add(f"  Origin              : {source_node.name} ({source_node.location})",
            "crit" if severity >= 70 else "warn")
        add(f"  Disruption Type     : {request.disruption_type}", "warn")
        add(f"  Declared Severity   : {severity:.0f}%  [{risk_lbl}]",
            "crit" if severity >= 70 else "warn")
        add(f"  Global GTI          : {gti_str}  (elevated tensions amplify cascade risk)", "info")
        add(f"  Sectors Affected    : {total_nodes}", "warn" if total_nodes > 0 else "info")
        add(f"  Propagation Depth   : {max_depth} level(s)", "info")
        if highest:
            add(f"  Highest Impact Node : {highest.name}  {highest.impact:.1f}%  [{_risk_label(highest.impact)}]",
                _risk_type(highest.impact))
        if live["events"]:
            add(f"  Live Events Found   : {len(live['events'])} active geopolitical events correlated to source node", "warn")
        if live["markets"]:
            chg_items = [(m.symbol, getattr(m, "change_percent", None)) for m in live["markets"] if getattr(m, "change_percent", None) is not None]
            if chg_items:
                worst = min(chg_items, key=lambda x: x[1])
                best  = max(chg_items, key=lambda x: x[1])
                add(f"  Market Movers       : {worst[0]} {worst[1]:+.2f}%  ↔  {best[0]} {best[1]:+.2f}%", "warn")
        add(f"  Variability Applied : {'Yes — stochastic noise' if request.apply_variability else 'No — deterministic'}", "info")
        add("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info")

        logger.info(
            "SC simulation: source=%s severity=%.0f affected=%d events=%d markets=%d gti=%s",
            source_node.name, severity, total_nodes,
            len(live["events"]), len(live["markets"]), gti_str,
        )

        # ── Persist ────────────────────────────────────────────────────────────
        affected_json = [n.model_dump() for n in affected_nodes]
        logs_json     = [lg.model_dump() for lg in logs]

        run = repo.create_simulation_run(
            source_node_id=source_node.id,
            source_node_name=source_node.name,
            severity=severity,
            disruption_type=request.disruption_type,
            apply_variability=request.apply_variability,
            affected_nodes_json=affected_json,
            logs_json=logs_json,
        )

        return SimulateResponse(
            id=run.id,
            source_node_id=run.source_node_id,
            source_node_name=run.source_node_name,
            severity=run.severity,
            disruption_type=run.disruption_type,
            apply_variability=run.apply_variability,
            affected_nodes=affected_nodes,
            logs=logs,
            created_at=run.created_at,
        )

    def get_simulation_history(self, db: Session, skip: int = 0, limit: int = 20) -> list:
        repo = SupplyChainRepository(db)
        runs = repo.get_simulation_runs(skip=skip, limit=limit)
        return [
            {
                "id": r.id,
                "source_node_id": r.source_node_id,
                "source_node_name": r.source_node_name,
                "severity": r.severity,
                "disruption_type": r.disruption_type,
                "affected_nodes": r.affected_nodes_json or [],
                "logs": r.logs_json or [],
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ]

    def _build_dependency_tree_recursive(self, node_id: int, nodes_map: dict, adjacency_map: dict, visited: set) -> Optional[DependencyTreeNode]:
        if node_id in visited:
            return None
        visited.add(node_id)

        node = nodes_map.get(node_id)
        if not node:
            return None

        children = []
        for dep in adjacency_map.get(node_id, []):
            child_id = dep.target_node_id
            child_node = nodes_map.get(child_id)
            if child_node:
                child_tree = self._build_dependency_tree_recursive(child_id, nodes_map, adjacency_map, visited.copy())
                children.append(DependencyTreeNode(
                    id=child_node.id,
                    name=child_node.name,
                    location=child_node.location,
                    type=child_node.type or "unknown",
                    strength=dep.dependency_strength,
                    dependency_type=dep.dependency_type,
                    children=child_tree.children if child_tree else []
                ))

        return DependencyTreeNode(
            id=node.id,
            name=node.name,
            location=node.location,
            type=node.type or "unknown",
            strength=None,
            dependency_type=None,
            children=children
        )

    def get_node_intelligence(self, db: Session, node_id: int) -> NodeIntelligenceResponse:
        repo = SupplyChainRepository(db)
        nodes_map = repo.get_all_nodes_map()
        adjacency = repo.get_adjacency_map()

        source_node = nodes_map.get(node_id)
        if not source_node:
            raise ValueError(f"Node with id={node_id} not found.")

        # 1. Overview
        overview = NodeOverview(
            id=source_node.id,
            name=source_node.name,
            location=source_node.location,
            type=source_node.type or "unknown"
        )

        # 2. Dependency Tree
        dependency_tree = self._build_dependency_tree_recursive(node_id, nodes_map, adjacency, set())

        # 3. Live Context
        live = _build_live_context(db, source_node.name)
        live_context = NodeLiveContext(
            events=[{
                "id": ev.id,
                "title": ev.title,
                "description": ev.description,
                "severity": ev.severity,
                "event_type": ev.event_type,
                "source": ev.source
            } for ev in live.get("events", [])],
            markets=[{
                "id": m.id,
                "symbol": m.symbol,
                "name": m.name,
                "price": m.price,
                "change_percent": getattr(m, "change_percent", None),
                "geo_sensitivity": m.geo_sensitivity
            } for m in live.get("markets", [])],
            gti_score=live.get("gti_score"),
            country_risk={
                "id": live["country_risk"].id,
                "country_code": live["country_risk"].country_code,
                "country_name": live["country_risk"].country_name,
                "risk_score": live["country_risk"].risk_score,
                "color_code": live["country_risk"].color_code,
                "sector_exposure": live["country_risk"].sector_exposure
            } if live.get("country_risk") else None
        )

        # 4. Impact Preview
        impact_preview = {}
        severities = [25.0, 50.0, 75.0, 100.0]
        for sev in severities:
            queue = deque([(node_id, sev, 0)])
            visited = {node_id}
            results = []
            while queue:
                curr_id, curr_impact, depth = queue.popleft()
                if depth > 0:
                    curr_node = nodes_map.get(curr_id)
                    if curr_node:
                        results.append(ImpactPreviewItem(
                            node_id=curr_id,
                            name=curr_node.name,
                            impact=round(curr_impact, 2),
                            depth=depth
                        ))
                for dep in adjacency.get(curr_id, []):
                    child_id = dep.target_node_id
                    if child_id not in visited:
                        strength = dep.dependency_strength or 0.5
                        child_impact = curr_impact * strength
                        if child_impact >= 1.0:
                            visited.add(child_id)
                            queue.append((child_id, child_impact, depth + 1))
            impact_preview[str(int(sev))] = results

        # 5. Chokepoint Analysis & Ranking
        rankings = []
        for n_id, n in nodes_map.items():
            deps = adjacency.get(n_id, [])
            score = sum(dep.dependency_strength or 0.0 for dep in deps)
            rankings.append((n_id, score))
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        chokepoint_score = 0.0
        rank = len(nodes_map)
        for idx, (n_id, score) in enumerate(rankings):
            if n_id == node_id:
                chokepoint_score = score
                rank = idx + 1
                break
        
        chokepoint_analysis = ChokepointAnalysisResult(
            is_chokepoint=(chokepoint_score >= 1.5),
            chokepoint_score=round(chokepoint_score, 4),
            rank=rank
        )

        # 6. Propagation Paths
        propagation_paths = []
        path_queue = deque([(node_id, [source_node.name], 1.0)])
        path_visited = {node_id}
        while path_queue:
            curr_id, path, strength = path_queue.popleft()
            if curr_id != node_id:
                curr_node = nodes_map.get(curr_id)
                if curr_node:
                    propagation_paths.append(PropagationPathItem(
                        target=curr_node.name,
                        path=path,
                        strength=round(strength, 4)
                    ))
            for dep in adjacency.get(curr_id, []):
                child_id = dep.target_node_id
                if child_id not in path_visited:
                    child_node = nodes_map.get(child_id)
                    if child_node:
                        path_visited.add(child_id)
                        new_strength = strength * (dep.dependency_strength or 0.5)
                        path_queue.append((child_id, path + [child_node.name], new_strength))

        return NodeIntelligenceResponse(
            overview=overview,
            dependency_tree=dependency_tree,
            live_context=live_context,
            impact_preview=impact_preview,
            chokepoint_analysis=chokepoint_analysis,
            propagation_paths=propagation_paths
        )


supply_chain_service = SupplyChainService()
