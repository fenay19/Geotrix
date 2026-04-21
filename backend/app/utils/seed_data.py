"""
Mock Data Seeder for GeoTrade AI Platform
==========================================
Run this script to populate the database with realistic mock data
for all features: Country Risk, Events, Markets, GTI, Supply Chain,
Trading Signals, and Simulation runs.

Usage:
    cd backend
    python -m app.utils.seed_data
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from datetime import datetime, timedelta
import random

from app.database.db import SessionLocal, engine
from app.database.base import Base
from app.models.country_risk_model import CountryRisk
from app.models.event_model import Event
from app.models.market_model import Market, MarketHistory
from app.models.gti_model import GTIScore, GTIHistory
from app.models.supply_chain_model import SupplyChainNode, SupplyChainDependency
from app.models.trading_signal_model import TradingSignal
from app.models.simulation_model import SimulationRun


def seed():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ──────────────────────────────────────────────
        # 1. COUNTRY RISKS
        # ──────────────────────────────────────────────
        countries = [
            {"country_code": "US", "country_name": "United States", "risk_score": 25.0, "color_code": "Green", "sector_exposure": {"Tech": 45, "Finance": 30, "Defense": 25}},
            {"country_code": "CN", "country_name": "China", "risk_score": 65.0, "color_code": "Red", "sector_exposure": {"Manufacturing": 40, "Tech": 35, "Real Estate": 25}},
            {"country_code": "TW", "country_name": "Taiwan", "risk_score": 82.0, "color_code": "Red", "sector_exposure": {"Semiconductors": 85, "Manufacturing": 15}},
            {"country_code": "RU", "country_name": "Russia", "risk_score": 78.0, "color_code": "Red", "sector_exposure": {"Energy": 65, "Defense": 35}},
            {"country_code": "UA", "country_name": "Ukraine", "risk_score": 90.0, "color_code": "Red", "sector_exposure": {"Agriculture": 50, "Energy": 30, "Defense": 20}},
            {"country_code": "SA", "country_name": "Saudi Arabia", "risk_score": 45.0, "color_code": "Yellow", "sector_exposure": {"Energy": 90, "Finance": 10}},
            {"country_code": "IR", "country_name": "Iran", "risk_score": 72.0, "color_code": "Red", "sector_exposure": {"Energy": 70, "Defense": 30}},
            {"country_code": "IL", "country_name": "Israel", "risk_score": 75.0, "color_code": "Red", "sector_exposure": {"Tech": 40, "Defense": 60}},
        ]

        country_objs = {}
        for c in countries:
            obj = CountryRisk(**c)
            db.add(obj)
            db.flush()
            country_objs[c["country_code"]] = obj
        print(f"[OK] Seeded {len(countries)} country risk records")

        # ──────────────────────────────────────────────
        # 2. EVENTS
        # ──────────────────────────────────────────────
        events_data = [
            {"title": "Taiwan Strait Military Drills", "description": "China conducts large-scale military exercises near Taiwan", "event_type": "war", "severity": 9, "impact_label": "CRITICAL", "source": "Reuters", "country_code": "TW"},
            {"title": "Russia-Ukraine Escalation", "description": "Renewed offensive in eastern Ukraine with heavy shelling", "event_type": "war", "severity": 10, "impact_label": "CRITICAL", "source": "BBC", "country_code": "UA"},
            {"title": "US Federal Reserve Rate Decision", "description": "Fed signals potential rate hike in upcoming meeting", "event_type": "economic", "severity": 7, "impact_label": "HIGH", "source": "Bloomberg", "country_code": "US"},
            {"title": "OPEC+ Production Cut", "description": "Saudi Arabia leads surprise oil production cut", "event_type": "economic", "severity": 8, "impact_label": "HIGH", "source": "CNBC", "country_code": "SA"},
            {"title": "Iran Nuclear Talks Collapse", "description": "Diplomatic negotiations break down, sanctions expected", "event_type": "sanctions", "severity": 8, "impact_label": "ELEVATED", "source": "Al Jazeera", "country_code": "IR"},
            {"title": "China Rare Earth Export Restrictions", "description": "Beijing imposes new limits on critical mineral exports", "event_type": "sanctions", "severity": 7, "impact_label": "HIGH", "source": "Financial Times", "country_code": "CN"},
            {"title": "Israel-Hamas Conflict Intensifies", "description": "Major military operation launched in Gaza Strip", "event_type": "war", "severity": 9, "impact_label": "CRITICAL", "source": "CNN", "country_code": "IL"},
            {"title": "US-China Tech Sanctions", "description": "US imposes new semiconductor export controls on China", "event_type": "sanctions", "severity": 8, "impact_label": "HIGH", "source": "WSJ", "country_code": "US"},
        ]

        now = datetime.utcnow()
        for i, e in enumerate(events_data):
            cc = e.pop("country_code")
            e["country_id"] = country_objs[cc].id
            e["timestamp"] = now - timedelta(hours=random.randint(1, 72))
            db.add(Event(**e))
        print(f"[OK] Seeded {len(events_data)} events")

        # ──────────────────────────────────────────────
        # 3. MARKETS
        # ──────────────────────────────────────────────
        markets_data = [
            {"symbol": "GOLD", "price": 2341.50, "category": "Commodity", "is_global": True},
            {"symbol": "OIL_BRENT", "price": 82.40, "category": "Commodity", "is_global": True},
            {"symbol": "SP500", "price": 5280.75, "category": "Index", "is_global": True},
            {"symbol": "XAUUSD", "price": 2341.50, "category": "Forex", "is_global": True},
            {"symbol": "BTCUSD", "price": 67500.00, "category": "Crypto", "is_global": True},
            {"symbol": "WTI", "price": 78.25, "category": "Commodity", "is_global": False, "country_code": "US"},
            {"symbol": "HSI", "price": 18420.00, "category": "Index", "is_global": False, "country_code": "CN"},
            {"symbol": "LMT", "price": 450.20, "category": "Stocks", "is_global": False, "country_code": "US"},
        ]

        market_objs = {}
        for m in markets_data:
            cc = m.pop("country_code", None)
            if cc:
                m["country_id"] = country_objs[cc].id
            obj = Market(**m)
            db.add(obj)
            db.flush()
            market_objs[m["symbol"]] = obj
        print(f"[OK] Seeded {len(markets_data)} market assets")

        # Generate 30 days of OHLC history per market
        history_count = 0
        for symbol, market_obj in market_objs.items():
            base_price = market_obj.price
            for day in range(30, 0, -1):
                noise = random.uniform(-0.02, 0.02)
                close_price = round(base_price * (1 + noise), 2)
                open_price = round(close_price * (1 + random.uniform(-0.01, 0.01)), 2)
                high_price = round(max(open_price, close_price) * (1 + random.uniform(0, 0.01)), 2)
                low_price = round(min(open_price, close_price) * (1 - random.uniform(0, 0.01)), 2)
                
                db.add(MarketHistory(
                    market_id=market_obj.id,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=random.randint(100000, 1000000),
                    timestamp=now - timedelta(days=day),
                ))
                history_count += 1
        print(f"[OK] Seeded {history_count} market history records")

        # ──────────────────────────────────────────────
        # 4. GTI SCORE & HISTORY
        # ──────────────────────────────────────────────
        gti = GTIScore(current_score=68.5, severity_category="High")
        db.add(gti)

        for day in range(30, 0, -1):
            score = round(random.uniform(45, 85), 1)
            db.add(GTIHistory(score=score, timestamp=now - timedelta(days=day)))
        print("[OK] Seeded GTI score + 30 days of history")

        # ──────────────────────────────────────────────
        # 5. SUPPLY CHAIN NODES & DEPENDENCIES
        # ──────────────────────────────────────────────
        nodes_data = [
            {"name": "Semiconductors", "location": "Taiwan", "type": "resource"},
            {"name": "Rare Earth Minerals", "location": "China", "type": "resource"},
            {"name": "Crude Oil", "location": "Saudi Arabia", "type": "resource"},
            {"name": "Natural Gas", "location": "Russia", "type": "resource"},
            {"name": "Tech Industry", "location": "Global", "type": "industry"},
            {"name": "Electronics Manufacturing", "location": "Global", "type": "industry"},
            {"name": "Energy Sector", "location": "Global", "type": "industry"},
            {"name": "Automotive Industry", "location": "Global", "type": "industry"},
            {"name": "Defense Sector", "location": "Global", "type": "industry"},
            {"name": "Agriculture / Grain", "location": "Ukraine", "type": "resource"},
        ]

        node_objs = {}
        for n in nodes_data:
            obj = SupplyChainNode(**n)
            db.add(obj)
            db.flush()
            node_objs[n["name"]] = obj

        # Country → Resource → Industry links
        deps = [
            ("Semiconductors", "Tech Industry", "critical_input", 0.95),
            ("Semiconductors", "Electronics Manufacturing", "critical_input", 0.90),
            ("Semiconductors", "Automotive Industry", "major_input", 0.70),
            ("Rare Earth Minerals", "Electronics Manufacturing", "critical_input", 0.85),
            ("Rare Earth Minerals", "Defense Sector", "major_input", 0.75),
            ("Crude Oil", "Energy Sector", "critical_input", 0.95),
            ("Crude Oil", "Automotive Industry", "major_input", 0.60),
            ("Natural Gas", "Energy Sector", "major_input", 0.80),
            ("Agriculture / Grain", "Energy Sector", "minor_input", 0.30),
        ]

        for src_name, tgt_name, dep_type, strength in deps:
            db.add(SupplyChainDependency(
                source_node_id=node_objs[src_name].id,
                target_node_id=node_objs[tgt_name].id,
                dependency_type=dep_type,
                dependency_strength=strength,
            ))
        print(f"[OK] Seeded {len(nodes_data)} supply chain nodes + {len(deps)} dependencies")

        # ──────────────────────────────────────────────
        # 6. TRADING SIGNALS
        # ──────────────────────────────────────────────
        signals_data = [
            {
                "symbol": "XAUUSD", 
                "signal_type": "BUY", 
                "confidence": 0.88, 
                "uncertainty": 0.12,
                "bullish_strength": 0.74,
                "bearish_strength": 0.08,
                "entry_price": 2341.0, 
                "stop_loss": 2298.0, 
                "target_price": 2427.0, 
                "risk_reward_ratio": 2.0,
                "atr": 1.84,
                "max_position_size": 3.2,
                "volatility_level": "Medium",
                "reasoning": "Safe-haven flows increasing due to elevated geopolitical stress.",
                "risk_factors": ["Sudden de-escalation", "Strong USD data"],
                "tags": ["short-term", "metals", "global"]
            },
            {
                "symbol": "HSI", 
                "signal_type": "SELL", 
                "confidence": 0.85, 
                "uncertainty": 0.15,
                "bullish_strength": 0.10,
                "bearish_strength": 0.60,
                "entry_price": 18420.0, 
                "stop_loss": 18800.0, 
                "target_price": 17200.0, 
                "risk_reward_ratio": 2.5,
                "atr": 2.1,
                "max_position_size": 2.5,
                "volatility_level": "High",
                "reasoning": "Tech sector exposure to supply chain decoupling risks.",
                "risk_factors": ["Policy stimulus surprise", "Yen weakness"],
                "tags": ["mid-term", "equity", "asia"]
            },
            {
                "symbol": "WTI", 
                "signal_type": "BUY", 
                "confidence": 0.85, 
                "uncertainty": 0.10,
                "bullish_strength": 0.65,
                "bearish_strength": 0.05,
                "entry_price": 78.0, 
                "stop_loss": 74.0, 
                "target_price": 88.0, 
                "risk_reward_ratio": 2.2,
                "atr": 1.5,
                "max_position_size": 3.0,
                "volatility_level": "High",
                "reasoning": "Supply disruptions in Middle East transit routes.",
                "risk_factors": ["OPEC production increase", "Global recession fears"],
                "tags": ["energy", "commodities"]
            },
            {
                "symbol": "LMT", 
                "signal_type": "BUY", 
                "confidence": 0.85, 
                "uncertainty": 0.05,
                "bullish_strength": 0.65,
                "bearish_strength": 0.15,
                "entry_price": 450.0, 
                "stop_loss": 435.0, 
                "target_price": 485.0, 
                "risk_reward_ratio": 2.3,
                "atr": 1.2,
                "max_position_size": 3.2,
                "volatility_level": "Medium",
                "reasoning": "Defense sector demand rising from global military escalations.",
                "risk_factors": ["Budget cuts", "Peace talks"],
                "tags": ["military", "defense", "stocks"]
            },
        ]

        for s in signals_data:
            sym = s.pop("symbol")
            s["market_id"] = market_objs[sym].id
            db.add(TradingSignal(**s))
        print(f"[OK] Seeded {len(signals_data)} trading signals")

        # ──────────────────────────────────────────────
        # 7. SIMULATION RUNS
        # ──────────────────────────────────────────────
        simulations_data = [
            {
                "scenario_name": "Taiwan Conflict",
                "region": "East Asia",
                "event_type": "war",
                "magnitude": "Severe",
                "results": {
                    "GOLD": {"direction": "UP", "impact_pct": 15.0},
                    "NASDAQ": {"direction": "DOWN", "impact_pct": -20.0},
                    "OIL_WTI": {"direction": "UP", "impact_pct": 25.0},
                    "sectors": {"Tech": "DOWN", "Defense": "UP", "Energy": "UP"},
                },
            },
            {
                "scenario_name": "OPEC+ Supply Shock",
                "region": "Middle East",
                "event_type": "economic",
                "magnitude": "Moderate",
                "results": {
                    "OIL_WTI": {"direction": "UP", "impact_pct": 18.0},
                    "GOLD": {"direction": "UP", "impact_pct": 5.0},
                    "NASDAQ": {"direction": "DOWN", "impact_pct": -5.0},
                    "sectors": {"Airlines": "DOWN", "Energy": "UP", "Transport": "DOWN"},
                },
            },
            {
                "scenario_name": "US Interest Rate Hike",
                "region": "North America",
                "event_type": "economic",
                "magnitude": "Moderate",
                "results": {
                    "SP500": {"direction": "DOWN", "impact_pct": -8.0},
                    "GOLD": {"direction": "DOWN", "impact_pct": -3.0},
                    "USD_EUR": {"direction": "UP", "impact_pct": 2.0},
                    "sectors": {"Real Estate": "DOWN", "Banking": "UP", "Tech": "DOWN"},
                },
            },
        ]

        for sim in simulations_data:
            db.add(SimulationRun(**sim))
        print(f"[OK] Seeded {len(simulations_data)} simulation runs")

        db.commit()
        print("\nAll mock data seeded successfully!")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
