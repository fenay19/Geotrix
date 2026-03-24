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
            {"country_code": "US", "country_name": "United States", "risk_score": 25.0, "color_code": "Green"},
            {"country_code": "CN", "country_name": "China", "risk_score": 65.0, "color_code": "Red"},
            {"country_code": "TW", "country_name": "Taiwan", "risk_score": 82.0, "color_code": "Red"},
            {"country_code": "RU", "country_name": "Russia", "risk_score": 78.0, "color_code": "Red"},
            {"country_code": "UA", "country_name": "Ukraine", "risk_score": 90.0, "color_code": "Red"},
            {"country_code": "SA", "country_name": "Saudi Arabia", "risk_score": 45.0, "color_code": "Yellow"},
            {"country_code": "IR", "country_name": "Iran", "risk_score": 72.0, "color_code": "Red"},
            {"country_code": "DE", "country_name": "Germany", "risk_score": 18.0, "color_code": "Green"},
            {"country_code": "JP", "country_name": "Japan", "risk_score": 22.0, "color_code": "Green"},
            {"country_code": "IN", "country_name": "India", "risk_score": 38.0, "color_code": "Yellow"},
            {"country_code": "KR", "country_name": "South Korea", "risk_score": 42.0, "color_code": "Yellow"},
            {"country_code": "GB", "country_name": "United Kingdom", "risk_score": 20.0, "color_code": "Green"},
            {"country_code": "IL", "country_name": "Israel", "risk_score": 75.0, "color_code": "Red"},
            {"country_code": "BR", "country_name": "Brazil", "risk_score": 30.0, "color_code": "Yellow"},
            {"country_code": "NG", "country_name": "Nigeria", "risk_score": 55.0, "color_code": "Yellow"},
        ]

        country_objs = {}
        for c in countries:
            obj = CountryRisk(**c)
            db.add(obj)
            db.flush()
            country_objs[c["country_code"]] = obj
        print(f"✅ Seeded {len(countries)} country risk records")

        # ──────────────────────────────────────────────
        # 2. EVENTS
        # ──────────────────────────────────────────────
        events_data = [
            {"title": "Taiwan Strait Military Drills", "description": "China conducts large-scale military exercises near Taiwan", "event_type": "war", "severity": 9, "source": "Reuters", "country_code": "TW"},
            {"title": "Russia-Ukraine Escalation", "description": "Renewed offensive in eastern Ukraine with heavy shelling", "event_type": "war", "severity": 10, "source": "BBC", "country_code": "UA"},
            {"title": "US Federal Reserve Rate Decision", "description": "Fed signals potential rate hike in upcoming meeting", "event_type": "economic", "severity": 7, "source": "Bloomberg", "country_code": "US"},
            {"title": "OPEC+ Production Cut", "description": "Saudi Arabia leads surprise oil production cut", "event_type": "economic", "severity": 8, "source": "CNBC", "country_code": "SA"},
            {"title": "Iran Nuclear Talks Collapse", "description": "Diplomatic negotiations break down, sanctions expected", "event_type": "sanctions", "severity": 8, "source": "Al Jazeera", "country_code": "IR"},
            {"title": "China Rare Earth Export Restrictions", "description": "Beijing imposes new limits on critical mineral exports", "event_type": "sanctions", "severity": 7, "source": "Financial Times", "country_code": "CN"},
            {"title": "India-Pakistan Border Tensions Rise", "description": "Military standoff reported along Line of Control", "event_type": "war", "severity": 6, "source": "Times of India", "country_code": "IN"},
            {"title": "Germany Industrial Output Decline", "description": "Manufacturing sector contracts for third consecutive quarter", "event_type": "economic", "severity": 5, "source": "DW", "country_code": "DE"},
            {"title": "Israel-Hamas Conflict Intensifies", "description": "Major military operation launched in Gaza Strip", "event_type": "war", "severity": 9, "source": "CNN", "country_code": "IL"},
            {"title": "Nigeria Oil Pipeline Attack", "description": "Armed group attacks major oil infrastructure", "event_type": "policy", "severity": 6, "source": "AFP", "country_code": "NG"},
            {"title": "US-China Tech Sanctions", "description": "US imposes new semiconductor export controls on China", "event_type": "sanctions", "severity": 8, "source": "WSJ", "country_code": "US"},
            {"title": "Japan Yen Intervention", "description": "Bank of Japan intervenes to support weakening yen", "event_type": "economic", "severity": 5, "source": "Nikkei", "country_code": "JP"},
        ]

        now = datetime.utcnow()
        for i, e in enumerate(events_data):
            cc = e.pop("country_code")
            e["country_id"] = country_objs[cc].id
            e["timestamp"] = now - timedelta(hours=random.randint(1, 72))
            db.add(Event(**e))
        print(f"✅ Seeded {len(events_data)} events")

        # ──────────────────────────────────────────────
        # 3. MARKETS
        # ──────────────────────────────────────────────
        markets_data = [
            {"symbol": "GOLD", "price": 2340.50},
            {"symbol": "OIL_WTI", "price": 78.25},
            {"symbol": "NASDAQ", "price": 18420.00},
            {"symbol": "SP500", "price": 5280.75},
            {"symbol": "USD_EUR", "price": 1.085},
            {"symbol": "USD_JPY", "price": 154.30},
            {"symbol": "BTC_USD", "price": 67500.00},
        ]

        market_objs = {}
        for m in markets_data:
            obj = Market(**m)
            db.add(obj)
            db.flush()
            market_objs[m["symbol"]] = obj
        print(f"✅ Seeded {len(markets_data)} market assets")

        # Generate 30 days of price history per market
        history_count = 0
        for symbol, market_obj in market_objs.items():
            base_price = market_obj.price
            for day in range(30, 0, -1):
                noise = random.uniform(-0.03, 0.03)
                hist_price = round(base_price * (1 + noise * (day / 10)), 2)
                db.add(MarketHistory(
                    market_id=market_obj.id,
                    price=hist_price,
                    timestamp=now - timedelta(days=day),
                ))
                history_count += 1
        print(f"✅ Seeded {history_count} market history records")

        # ──────────────────────────────────────────────
        # 4. GTI SCORE & HISTORY
        # ──────────────────────────────────────────────
        gti = GTIScore(current_score=68.5, severity_category="High")
        db.add(gti)

        for day in range(30, 0, -1):
            score = round(random.uniform(45, 85), 1)
            db.add(GTIHistory(score=score, timestamp=now - timedelta(days=day)))
        print("✅ Seeded GTI score + 30 days of history")

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
        print(f"✅ Seeded {len(nodes_data)} supply chain nodes + {len(deps)} dependencies")

        # ──────────────────────────────────────────────
        # 6. TRADING SIGNALS
        # ──────────────────────────────────────────────
        signals_data = [
            {"symbol": "GOLD", "signal_type": "BUY", "confidence": 0.85, "entry_price": 2340.0, "stop_loss": 2280.0, "target_price": 2450.0, "reasoning": "GTI score above 65 + active military conflicts drive safe-haven demand."},
            {"symbol": "OIL_WTI", "signal_type": "BUY", "confidence": 0.78, "entry_price": 78.0, "stop_loss": 74.0, "target_price": 86.0, "reasoning": "OPEC+ production cut + Middle East tensions restrict supply."},
            {"symbol": "NASDAQ", "signal_type": "SELL", "confidence": 0.72, "entry_price": 18420.0, "stop_loss": 18800.0, "target_price": 17500.0, "reasoning": "Semiconductor supply risk from Taiwan tensions + rate hike fears."},
            {"symbol": "SP500", "signal_type": "HOLD", "confidence": 0.55, "entry_price": None, "stop_loss": None, "target_price": None, "reasoning": "Mixed signals: defensive sectors up, tech sector under pressure."},
        ]

        for s in signals_data:
            sym = s.pop("symbol")
            s["market_id"] = market_objs[sym].id
            db.add(TradingSignal(**s))
        print(f"✅ Seeded {len(signals_data)} trading signals")

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
        print(f"✅ Seeded {len(simulations_data)} simulation runs")

        db.commit()
        print("\n🎉 All mock data seeded successfully!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
