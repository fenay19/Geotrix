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

from datetime import datetime, timedelta, timezone
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
    # Clear existing tables first
    Base.metadata.drop_all(bind=engine)
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
            {"country_code": "JP", "country_name": "Japan", "risk_score": 30.0, "color_code": "Green", "sector_exposure": {"Manufacturing": 40, "Tech": 30, "Finance": 30}},
            {"country_code": "DE", "country_name": "Germany", "risk_score": 28.0, "color_code": "Green", "sector_exposure": {"Manufacturing": 50, "Automotive": 30, "Finance": 20}},
            {"country_code": "IN", "country_name": "India", "risk_score": 40.0, "color_code": "Yellow", "sector_exposure": {"Tech": 40, "Services": 40, "Agriculture": 20}},
            {"country_code": "KR", "country_name": "South Korea", "risk_score": 35.0, "color_code": "Green", "sector_exposure": {"Semiconductors": 60, "Tech": 30, "Manufacturing": 10}},
            {"country_code": "BR", "country_name": "Brazil", "risk_score": 50.0, "color_code": "Yellow", "sector_exposure": {"Agriculture": 40, "Energy": 30, "Materials": 30}},
            {"country_code": "MX", "country_name": "Mexico", "risk_score": 48.0, "color_code": "Yellow", "sector_exposure": {"Manufacturing": 50, "Energy": 20, "Agriculture": 30}},
            {"country_code": "GB", "country_name": "United Kingdom", "risk_score": 27.0, "color_code": "Green", "sector_exposure": {"Finance": 50, "Services": 30, "Energy": 20}},
            {"country_code": "FR", "country_name": "France", "risk_score": 26.0, "color_code": "Green", "sector_exposure": {"Finance": 30, "Luxury": 40, "Industrial": 30}},
            {"country_code": "CA", "country_name": "Canada", "risk_score": 24.0, "color_code": "Green", "sector_exposure": {"Energy": 35, "Finance": 30, "Manufacturing": 25}},
            {"country_code": "AU", "country_name": "Australia", "risk_score": 23.0, "color_code": "Green", "sector_exposure": {"Materials": 50, "Finance": 30, "Energy": 20}},
            {"country_code": "TR", "country_name": "Turkey", "risk_score": 55.0, "color_code": "Yellow", "sector_exposure": {"Manufacturing": 45, "Services": 35, "Agriculture": 20}},
            {"country_code": "ZA", "country_name": "South Africa", "risk_score": 52.0, "color_code": "Yellow", "sector_exposure": {"Materials": 40, "Finance": 30, "Manufacturing": 20}},
            {"country_code": "ID", "country_name": "Indonesia", "risk_score": 42.0, "color_code": "Yellow", "sector_exposure": {"Energy": 40, "Agriculture": 35, "Materials": 25}},
            {"country_code": "PK", "country_name": "Pakistan", "risk_score": 68.0, "color_code": "Red", "sector_exposure": {"Agriculture": 55, "Textiles": 30, "Services": 15}},
            {"country_code": "KP", "country_name": "North Korea", "risk_score": 85.0, "color_code": "Red", "sector_exposure": {"Defense": 80, "Mining": 20}},
            {"country_code": "IT", "country_name": "Italy", "risk_score": 32.0, "color_code": "Green", "sector_exposure": {"Manufacturing": 45, "Finance": 25, "Tourism": 30}},
            {"country_code": "ES", "country_name": "Spain", "risk_score": 33.0, "color_code": "Green", "sector_exposure": {"Tourism": 40, "Manufacturing": 30, "Services": 30}},
            {"country_code": "NL", "country_name": "Netherlands", "risk_score": 25.0, "color_code": "Green", "sector_exposure": {"Tech": 40, "Logistics": 40, "Agriculture": 20}},
            {"country_code": "SG", "country_name": "Singapore", "risk_score": 22.0, "color_code": "Green", "sector_exposure": {"Finance": 50, "Tech": 35, "Logistics": 15}},
            {"country_code": "CH", "country_name": "Switzerland", "risk_score": 21.0, "color_code": "Green", "sector_exposure": {"Finance": 55, "Pharma": 35, "Tech": 10}},
            {"country_code": "PL", "country_name": "Poland", "risk_score": 38.0, "color_code": "Yellow", "sector_exposure": {"Manufacturing": 45, "Tech": 30, "Agriculture": 25}},
            {"country_code": "VN", "country_name": "Vietnam", "risk_score": 41.0, "color_code": "Yellow", "sector_exposure": {"Manufacturing": 60, "Agriculture": 25, "Tech": 15}},
            {"country_code": "PH", "country_name": "Philippines", "risk_score": 44.0, "color_code": "Yellow", "sector_exposure": {"Services": 50, "Manufacturing": 25, "Agriculture": 25}},
            {"country_code": "MY", "country_name": "Malaysia", "risk_score": 36.0, "color_code": "Yellow", "sector_exposure": {"Tech": 45, "Energy": 35, "Agriculture": 20}},
            {"country_code": "TH", "country_name": "Thailand", "risk_score": 39.0, "color_code": "Yellow", "sector_exposure": {"Manufacturing": 40, "Tourism": 35, "Agriculture": 25}},
            {"country_code": "EG", "country_name": "Egypt", "risk_score": 58.0, "color_code": "Yellow", "sector_exposure": {"Services": 45, "Energy": 35, "Agriculture": 20}},
            {"country_code": "NG", "country_name": "Nigeria", "risk_score": 62.0, "color_code": "Yellow", "sector_exposure": {"Energy": 75, "Agriculture": 15, "Services": 10}},
            {"country_code": "AR", "country_name": "Argentina", "risk_score": 56.0, "color_code": "Yellow", "sector_exposure": {"Agriculture": 50, "Materials": 25, "Services": 25}},
            {"country_code": "CO", "country_name": "Colombia", "risk_score": 49.0, "color_code": "Yellow", "sector_exposure": {"Energy": 40, "Agriculture": 35, "Services": 25}},
            {"country_code": "CL", "country_name": "Chile", "risk_score": 34.0, "color_code": "Green", "sector_exposure": {"Materials": 65, "Agriculture": 20, "Services": 15}},
            {"country_code": "QA", "country_name": "Qatar", "risk_score": 31.0, "color_code": "Green", "sector_exposure": {"Energy": 85, "Finance": 15}},
            {"country_code": "AE", "country_name": "United Arab Emirates", "risk_score": 33.0, "color_code": "Green", "sector_exposure": {"Energy": 55, "Finance": 30, "Trade": 15}}
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
            {"title": "Taiwan Strait Military Drills", "description": "China conducts large-scale military exercises near Taiwan", "event_type": "war", "severity": 9, "impact_label": "CRITICAL", "source": "Reuters", "country_code": "TW", "casualties": 0, "economic_damage": 50.0, "infrastructure_destruction": "Minimal", "displaced_population": 0, "impact_factor": 1.0, "escalation_potential": 8},
            {"title": "Russia-Ukraine Escalation", "description": "Renewed offensive in eastern Ukraine with heavy shelling", "event_type": "war", "severity": 10, "impact_label": "CRITICAL", "source": "BBC", "country_code": "UA", "casualties": 350, "economic_damage": 1200.0, "infrastructure_destruction": "Severe", "displaced_population": 45000, "impact_factor": 1.75, "escalation_potential": 9},
            {"title": "US Federal Reserve Rate Decision", "description": "Fed signals potential rate hike in upcoming meeting", "event_type": "economic", "severity": 7, "impact_label": "HIGH", "source": "Bloomberg", "country_code": "US", "casualties": 0, "economic_damage": 2000.0, "infrastructure_destruction": "Minimal", "displaced_population": 0, "impact_factor": 1.3, "escalation_potential": 4},
            {"title": "OPEC+ Production Cut", "description": "Saudi Arabia leads surprise oil production cut", "event_type": "economic", "severity": 8, "impact_label": "HIGH", "source": "CNBC", "country_code": "SA", "casualties": 0, "economic_damage": 1500.0, "infrastructure_destruction": "Minimal", "displaced_population": 0, "impact_factor": 1.3, "escalation_potential": 6},
            {"title": "Iran Nuclear Talks Collapse", "description": "Diplomatic negotiations break down, sanctions expected", "event_type": "sanctions", "severity": 8, "impact_label": "ELEVATED", "source": "Al Jazeera", "country_code": "IR", "casualties": 0, "economic_damage": 80.0, "infrastructure_destruction": "Minimal", "displaced_population": 0, "impact_factor": 1.0, "escalation_potential": 7},
            {"title": "China Rare Earth Export Restrictions", "description": "Beijing imposes new limits on critical mineral exports", "event_type": "sanctions", "severity": 7, "impact_label": "HIGH", "source": "Financial Times", "country_code": "CN", "casualties": 0, "economic_damage": 300.0, "infrastructure_destruction": "Minimal", "displaced_population": 0, "impact_factor": 1.15, "escalation_potential": 6},
            {"title": "Israel-Hamas Conflict Intensifies", "description": "Major military operation launched in Gaza Strip", "event_type": "war", "severity": 9, "impact_label": "CRITICAL", "source": "CNN", "country_code": "IL", "casualties": 550, "economic_damage": 450.0, "infrastructure_destruction": "Severe", "displaced_population": 120000, "impact_factor": 1.85, "escalation_potential": 8},
            {"title": "US-China Tech Sanctions", "description": "US imposes new semiconductor export controls on China", "event_type": "sanctions", "severity": 8, "impact_label": "HIGH", "source": "WSJ", "country_code": "US", "casualties": 0, "economic_damage": 500.0, "infrastructure_destruction": "Minimal", "displaced_population": 0, "impact_factor": 1.15, "escalation_potential": 7},
        ]

        now = datetime.now(timezone.utc)
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

        # Generate 180 days of OHLC history per market
        history_count = 0
        for symbol, market_obj in market_objs.items():
            base_price = market_obj.price
            for day in range(180, 0, -1):
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

        for day in range(180, 0, -1):
            score = round(random.uniform(45, 85), 1)
            db.add(GTIHistory(score=score, timestamp=now - timedelta(days=day)))
        print("[OK] Seeded GTI score + 30 days of history")

        # ──────────────────────────────────────────────
        # 5. SUPPLY CHAIN NODES & DEPENDENCIES
        # ──────────────────────────────────────────────
        nodes_data = [
            {"name": "Semiconductors", "location": "Taiwan", "type": "choke_point"},
            {"name": "Rare Earth Minerals", "location": "China", "type": "choke_point"},
            {"name": "Crude Oil", "location": "Saudi Arabia", "type": "choke_point"},
            {"name": "Natural Gas", "location": "Russia", "type": "choke_point"},
            {"name": "Tech Industry", "location": "Global", "type": "production"},
            {"name": "Electronics Manufacturing", "location": "Global", "type": "production"},
            {"name": "Energy Sector", "location": "Global", "type": "port"},
            {"name": "Automotive Industry", "location": "Global", "type": "production"},
            {"name": "Defense Sector", "location": "Global", "type": "production"},
            {"name": "Agriculture / Grain", "location": "Ukraine", "type": "production"},
            {"name": "Advanced Lithography (EUV)", "location": "Netherlands", "type": "choke_point"},
            {"name": "Lithium / Battery Cells", "location": "Australia", "type": "choke_point"},
            {"name": "Cobalt Mining", "location": "DR Congo", "type": "choke_point"},
            {"name": "Suez Canal Transit", "location": "Egypt", "type": "port"},
            {"name": "Strait of Malacca Transit", "location": "Singapore", "type": "port"},
            {"name": "Potash / Fertilizers", "location": "Canada", "type": "production"},
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
            ("Natural Gas", "Energy Sector", "pipeline", 0.80),
            ("Agriculture / Grain", "Energy Sector", "minor_input", 0.30),
            ("Advanced Lithography (EUV)", "Semiconductors", "critical_input", 0.98),
            ("Lithium / Battery Cells", "Automotive Industry", "major_input", 0.85),
            ("Lithium / Battery Cells", "Electronics Manufacturing", "major_input", 0.75),
            ("Cobalt Mining", "Lithium / Battery Cells", "critical_input", 0.80),
            ("Crude Oil", "Suez Canal Transit", "pipeline", 0.85),
            ("Suez Canal Transit", "Energy Sector", "critical_input", 0.90),
            ("Crude Oil", "Strait of Malacca Transit", "critical_input", 0.75),
            ("Strait of Malacca Transit", "Electronics Manufacturing", "major_input", 0.80),
            ("Potash / Fertilizers", "Agriculture / Grain", "major_input", 0.70),
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
        # Auto-generate trading signals dynamically for all seeded markets
        from app.services.signal_service import signal_service
        auto_gen_count = 0
        for sym, market_obj in market_objs.items():
            try:
                signal_service.auto_generate_signal(db, market_obj.id)
                auto_gen_count += 1
            except Exception as e:
                print(f"[WARN] Failed to auto-generate signal for {sym}: {e}")
        print(f"[OK] Auto-generated trading signals for {auto_gen_count} markets")

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
