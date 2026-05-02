"""
GeoTrade AI — Market Seeder
============================
Seeds 35 assets across 7 asset classes when the markets table is empty.
Called at application startup from main.py lifespan.
"""

import logging
from sqlalchemy.orm import Session
from ..models.market_model import Market

logger = logging.getLogger("geotrade.database.seed_markets")

# fmt: off
SEED_MARKETS = [
    # ── Equity Indices ──────────────────────────────────────────────────────────
    {"symbol": "SPY",    "name": "S&P 500 SPDR ETF",         "category": "Index",     "asset_class": "Indices",     "is_global": True,  "price": 524.50, "geo_sensitivity": 0.65},
    {"symbol": "QQQ",    "name": "Nasdaq-100 ETF",            "category": "Index",     "asset_class": "Indices",     "is_global": True,  "price": 447.30, "geo_sensitivity": 0.60},
    {"symbol": "IWM",    "name": "Russell 2000 ETF",          "category": "Index",     "asset_class": "Indices",     "is_global": True,  "price": 198.20, "geo_sensitivity": 0.50},
    {"symbol": "EEM",    "name": "Emerging Markets ETF",      "category": "Index",     "asset_class": "Indices",     "is_global": True,  "price": 41.80,  "geo_sensitivity": 0.85},
    {"symbol": "DIA",    "name": "Dow Jones ETF",             "category": "Index",     "asset_class": "Indices",     "is_global": True,  "price": 392.10, "geo_sensitivity": 0.55},
    {"symbol": "SP500",  "name": "S&P 500 Index",            "category": "Index",     "asset_class": "Indices",     "is_global": True,  "price": 5280.75, "geo_sensitivity": 0.65},
    {"symbol": "HSI",    "name": "Hang Seng Index",          "category": "Index",     "asset_class": "Indices",     "is_global": True,  "price": 18420.00, "geo_sensitivity": 0.85},

    # ── Stocks ──────────────────────────────────────────────────────────────────
    {"symbol": "LMT",    "name": "Lockheed Martin",           "category": "Equity",    "asset_class": "Stocks",      "is_global": True,  "price": 468.20, "geo_sensitivity": 0.95},
    {"symbol": "RTX",    "name": "RTX Corporation",           "category": "Equity",    "asset_class": "Stocks",      "is_global": True,  "price": 122.40, "geo_sensitivity": 0.92},
    {"symbol": "BA",     "name": "Boeing Company",            "category": "Equity",    "asset_class": "Stocks",      "is_global": True,  "price": 176.90, "geo_sensitivity": 0.80},
    {"symbol": "AAPL",   "name": "Apple Inc.",                "category": "Equity",    "asset_class": "Stocks",      "is_global": True,  "price": 211.60, "geo_sensitivity": 0.55},
    {"symbol": "NVDA",   "name": "NVIDIA Corporation",        "category": "Equity",    "asset_class": "Stocks",      "is_global": True,  "price": 131.80, "geo_sensitivity": 0.70},
    {"symbol": "MSFT",   "name": "Microsoft Corporation",     "category": "Equity",    "asset_class": "Stocks",      "is_global": True,  "price": 432.20, "geo_sensitivity": 0.45},
    {"symbol": "XOM",    "name": "Exxon Mobil",               "category": "Equity",    "asset_class": "Stocks",      "is_global": True,  "price": 108.50, "geo_sensitivity": 0.88},

    # ── ETFs ────────────────────────────────────────────────────────────────────
    {"symbol": "GLD",    "name": "Gold SPDR ETF",             "category": "Commodity", "asset_class": "ETFs",        "is_global": True,  "price": 228.40, "geo_sensitivity": 0.90},
    {"symbol": "ITA",    "name": "iShares Defense ETF",       "category": "Equity",    "asset_class": "ETFs",        "is_global": True,  "price": 128.70, "geo_sensitivity": 0.93},
    {"symbol": "XLE",    "name": "Energy Select SPDR ETF",    "category": "Commodity", "asset_class": "ETFs",        "is_global": True,  "price": 87.30,  "geo_sensitivity": 0.85},
    {"symbol": "XLF",    "name": "Financial Select ETF",      "category": "Equity",    "asset_class": "ETFs",        "is_global": True,  "price": 43.10,  "geo_sensitivity": 0.60},
    {"symbol": "GDX",    "name": "Gold Miners ETF",           "category": "Commodity", "asset_class": "ETFs",        "is_global": True,  "price": 37.80,  "geo_sensitivity": 0.88},
    {"symbol": "INDA",   "name": "iShares MSCI India ETF",   "category": "Equity",    "asset_class": "ETFs",        "is_global": True,  "price": 47.77,  "geo_sensitivity": 0.70},

    # ── Commodities ─────────────────────────────────────────────────────────────
    {"symbol": "GOLD",   "name": "Gold Futures",              "category": "Commodity", "asset_class": "Commodities", "is_global": True,  "price": 2350.00, "geo_sensitivity": 0.92},
    {"symbol": "OIL_BRENT", "name": "Brent Crude Oil",       "category": "Commodity", "asset_class": "Commodities", "is_global": True,  "price": 83.20,  "geo_sensitivity": 0.95},
    {"symbol": "SI=F",   "name": "Silver Futures",            "category": "Commodity", "asset_class": "Commodities", "is_global": True,  "price": 29.10,  "geo_sensitivity": 0.78},
    {"symbol": "NG=F",   "name": "Natural Gas Futures",       "category": "Commodity", "asset_class": "Commodities", "is_global": True,  "price": 2.44,   "geo_sensitivity": 0.82},
    {"symbol": "WTI",    "name": "WTI Crude Oil",            "category": "Commodity", "asset_class": "Commodities", "is_global": True,  "price": 78.25,  "geo_sensitivity": 0.95},
    {"symbol": "XAUUSD", "name": "Gold Spot/USD",            "category": "Commodity", "asset_class": "Commodities", "is_global": True,  "price": 2341.50, "geo_sensitivity": 0.90},

    # ── Forex ───────────────────────────────────────────────────────────────────
    {"symbol": "EURUSD=X", "name": "EUR/USD",                 "category": "Currency",  "asset_class": "Forex",       "is_global": True,  "price": 1.0840, "geo_sensitivity": 0.72},
    {"symbol": "USDJPY=X", "name": "USD/JPY",                 "category": "Currency",  "asset_class": "Forex",       "is_global": True,  "price": 157.20, "geo_sensitivity": 0.68},
    {"symbol": "GBPUSD=X", "name": "GBP/USD",                 "category": "Currency",  "asset_class": "Forex",       "is_global": True,  "price": 1.2740, "geo_sensitivity": 0.65},
    {"symbol": "USDCNH=X", "name": "USD/CNH",                 "category": "Currency",  "asset_class": "Forex",       "is_global": True,  "price": 7.2450, "geo_sensitivity": 0.80},
    {"symbol": "AUDUSD=X", "name": "AUD/USD",                 "category": "Currency",  "asset_class": "Forex",       "is_global": True,  "price": 0.6560, "geo_sensitivity": 0.62},

    # ── Crypto ──────────────────────────────────────────────────────────────────
    {"symbol": "BTCUSD",  "name": "Bitcoin",                  "category": "Crypto",    "asset_class": "Crypto",      "is_global": True,  "price": 67200.0, "geo_sensitivity": 0.55},
    {"symbol": "ETH-USD", "name": "Ethereum",                 "category": "Crypto",    "asset_class": "Crypto",      "is_global": True,  "price": 3520.0,  "geo_sensitivity": 0.50},
    {"symbol": "SOL-USD", "name": "Solana",                   "category": "Crypto",    "asset_class": "Crypto",      "is_global": True,  "price": 168.40,  "geo_sensitivity": 0.45},

    # ── Bonds ───────────────────────────────────────────────────────────────────
    {"symbol": "TLT",    "name": "20+ Year Treasury ETF",     "category": "Bond",      "asset_class": "Bonds",       "is_global": True,  "price": 88.20,  "geo_sensitivity": 0.70},
    {"symbol": "SHY",    "name": "1-3 Year Treasury ETF",     "category": "Bond",      "asset_class": "Bonds",       "is_global": True,  "price": 81.40,  "geo_sensitivity": 0.40},
    {"symbol": "HYG",    "name": "High Yield Bond ETF",       "category": "Bond",      "asset_class": "Bonds",       "is_global": True,  "price": 77.60,  "geo_sensitivity": 0.65},
    {"symbol": "BND",    "name": "Vanguard Total Bond ETF",   "category": "Bond",      "asset_class": "Bonds",       "is_global": True,  "price": 72.30,  "geo_sensitivity": 0.45},
]
# fmt: on


def seed_markets(db: Session) -> int:
    """
    Seeds/upserts the markets table with the 35 custom assets.
    Ensures all assets have their name, category, asset_class, is_global, and geo_sensitivity populated.
    Returns the number of new markets inserted.
    """
    inserted = 0
    updated = 0
    for data in SEED_MARKETS:
        existing = db.query(Market).filter(Market.symbol == data["symbol"]).first()
        if existing:
            # Update fields if they are different or null
            changed = False
            for k, v in data.items():
                if getattr(existing, k) != v:
                    setattr(existing, k, v)
                    changed = True
            if changed:
                updated += 1
        else:
            market = Market(**data)
            db.add(market)
            inserted += 1

    if inserted > 0 or updated > 0:
        db.commit()
        logger.info("Market seeder: inserted %d new assets, updated %d assets.", inserted, updated)
    return inserted
