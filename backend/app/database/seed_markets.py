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
COUNTRY_ASSET_MAP = {
    "US": ["SPY", "AAPL", "MSFT"],
    "CN": ["FXI", "USDCNH=X"],
    "TW": ["TSM"],
    "JP": ["EWJ"],
    "DE": ["EWG"],
    "IN": ["INDA"],
    "KR": ["EWY"],
    "RU": ["USDRUB=X"],
    "UA": ["USDUAH=X"],
    "SA": ["KSA"],
    "IL": ["EIS"],
    "BR": ["EWZ"],
    "MX": ["EWW"],
    "GB": ["EWU"],
    "FR": ["EWQ"]
}

# Create a reverse mapping for easy lookup
ASSET_TO_COUNTRY_MAP = {}
for cc, symbols in COUNTRY_ASSET_MAP.items():
    for sym in symbols:
        ASSET_TO_COUNTRY_MAP[sym] = cc

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
    {"symbol": "TSM",    "name": "Taiwan Semiconductor Mfg",   "category": "Equity",    "asset_class": "Stocks",      "is_global": False, "price": 175.50, "geo_sensitivity": 0.90},

    # ── ETFs ────────────────────────────────────────────────────────────────────
    {"symbol": "GLD",    "name": "Gold SPDR ETF",             "category": "Commodity", "asset_class": "ETFs",        "is_global": True,  "price": 228.40, "geo_sensitivity": 0.90},
    {"symbol": "ITA",    "name": "iShares Defense ETF",       "category": "Equity",    "asset_class": "ETFs",        "is_global": True,  "price": 128.70, "geo_sensitivity": 0.93},
    {"symbol": "XLE",    "name": "Energy Select SPDR ETF",    "category": "Commodity", "asset_class": "ETFs",        "is_global": True,  "price": 87.30,  "geo_sensitivity": 0.85},
    {"symbol": "XLF",    "name": "Financial Select ETF",      "category": "Equity",    "asset_class": "ETFs",        "is_global": True,  "price": 43.10,  "geo_sensitivity": 0.60},
    {"symbol": "GDX",    "name": "Gold Miners ETF",           "category": "Commodity", "asset_class": "ETFs",        "is_global": True,  "price": 37.80,  "geo_sensitivity": 0.88},
    {"symbol": "INDA",   "name": "iShares MSCI India ETF",   "category": "Equity",    "asset_class": "ETFs",        "is_global": True,  "price": 47.77,  "geo_sensitivity": 0.70},
    {"symbol": "FXI",    "name": "iShares China Large-Cap ETF", "category": "Equity",    "asset_class": "ETFs",        "is_global": False, "price": 26.20,  "geo_sensitivity": 0.85},
    {"symbol": "EWJ",    "name": "iShares MSCI Japan ETF",     "category": "Equity",    "asset_class": "ETFs",        "is_global": False, "price": 70.80,  "geo_sensitivity": 0.70},
    {"symbol": "EWG",    "name": "iShares MSCI Germany ETF",   "category": "Equity",    "asset_class": "ETFs",        "is_global": False, "price": 34.50,  "geo_sensitivity": 0.72},
    {"symbol": "EWY",    "name": "iShares MSCI South Korea",   "category": "Equity",    "asset_class": "ETFs",        "is_global": False, "price": 65.40,  "geo_sensitivity": 0.75},
    {"symbol": "KSA",    "name": "iShares MSCI Saudi Arabia",  "category": "Equity",    "asset_class": "ETFs",        "is_global": False, "price": 42.10,  "geo_sensitivity": 0.78},
    {"symbol": "EIS",    "name": "iShares MSCI Israel ETF",    "category": "Equity",    "asset_class": "ETFs",        "is_global": False, "price": 58.60,  "geo_sensitivity": 0.88},
    {"symbol": "EWZ",    "name": "iShares MSCI Brazil ETF",    "category": "Equity",    "asset_class": "ETFs",        "is_global": False, "price": 31.20,  "geo_sensitivity": 0.74},
    {"symbol": "EWW",    "name": "iShares MSCI Mexico ETF",    "category": "Equity",    "asset_class": "ETFs",        "is_global": False, "price": 60.50,  "geo_sensitivity": 0.76},
    {"symbol": "EWU",    "name": "iShares MSCI UK ETF",        "category": "Equity",    "asset_class": "ETFs",        "is_global": False, "price": 35.80,  "geo_sensitivity": 0.65},
    {"symbol": "EWQ",    "name": "iShares MSCI France ETF",    "category": "Equity",    "asset_class": "ETFs",        "is_global": False, "price": 38.20,  "geo_sensitivity": 0.68},

    # ── Commodities ─────────────────────────────────────────────────────────────
    {"symbol": "GOLD",   "name": "Gold Futures",              "category": "Commodity", "asset_class": "Commodities", "is_global": True,  "price": 2350.00, "geo_sensitivity": 0.92},
    {"symbol": "OIL_BRENT", "name": "Brent Crude Oil",       "category": "Commodity", "asset_class": "Commodities", "is_global": True,  "price": 83.20,  "geo_sensitivity": 0.95},
    {"symbol": "SI=F",   "name": "Silver Futures",            "category": "Commodity", "asset_class": "Commodities", "is_global": True,  "price": 29.10,  "geo_sensitivity": 0.78},
    {"symbol": "NG=F",   "name": "Natural Gas Futures",       "category": "Commodity", "asset_class": "Commodities", "is_global": True,  "price": 2.44,   "geo_sensitivity": 0.82},
    {"symbol": "WTI",    "name": "WTI Crude Oil",            "category": "Commodity", "asset_class": "Commodities", "is_global": True,  "price": 78.25,  "geo_sensitivity": 0.95},
    {"symbol": "XAUUSD", "name": "Gold Spot/USD",            "category": "Commodity", "asset_class": "Commodities", "is_global": True,  "price": 2341.50, "geo_sensitivity": 0.90},
    {"symbol": "GC=F",    "name": "Gold Futures (Global)",      "category": "Commodity", "asset_class": "Commodities", "is_global": True,  "price": 2350.00, "geo_sensitivity": 0.92},
    {"symbol": "CL=F",    "name": "Crude Oil Futures (Global)", "category": "Commodity", "asset_class": "Commodities", "is_global": True,  "price": 78.25,  "geo_sensitivity": 0.95},

    # ── Forex ───────────────────────────────────────────────────────────────────
    {"symbol": "EURUSD=X", "name": "EUR/USD",                 "category": "Currency",  "asset_class": "Forex",       "is_global": True,  "price": 1.0840, "geo_sensitivity": 0.72},
    {"symbol": "USDJPY=X", "name": "USD/JPY",                 "category": "Currency",  "asset_class": "Forex",       "is_global": True,  "price": 157.20, "geo_sensitivity": 0.68},
    {"symbol": "GBPUSD=X", "name": "GBP/USD",                 "category": "Currency",  "asset_class": "Forex",       "is_global": True,  "price": 1.2740, "geo_sensitivity": 0.65},
    {"symbol": "USDCNH=X", "name": "USD/CNH",                 "category": "Currency",  "asset_class": "Forex",       "is_global": True,  "price": 7.2450, "geo_sensitivity": 0.80},
    {"symbol": "AUDUSD=X", "name": "AUD/USD",                 "category": "Currency",  "asset_class": "Forex",       "is_global": True,  "price": 0.6560, "geo_sensitivity": 0.62},
    {"symbol": "USDRUB=X", "name": "USD/RUB",                   "category": "Currency",  "asset_class": "Forex",       "is_global": False, "price": 89.50,  "geo_sensitivity": 0.92},
    {"symbol": "USDUAH=X", "name": "USD/UAH",                   "category": "Currency",  "asset_class": "Forex",       "is_global": False, "price": 40.20,  "geo_sensitivity": 0.95},

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
    Seeds/upserts the markets table with the custom assets.
    Ensures all assets have their name, category, asset_class, is_global, geo_sensitivity, and country_id populated.
    Returns the number of new markets inserted.
    """
    from ..models.country_risk_model import CountryRisk
    inserted = 0
    updated = 0
    for data in SEED_MARKETS:
        # Resolve country_id dynamically
        symbol = data["symbol"]
        cc = ASSET_TO_COUNTRY_MAP.get(symbol)
        resolved_country_id = None
        if cc:
            country = db.query(CountryRisk).filter(CountryRisk.country_code == cc).first()
            if country:
                resolved_country_id = country.id
            else:
                logger.warning("Country code '%s' for asset '%s' not found in country_risks table. Skipping country association.", cc, symbol)

        existing = db.query(Market).filter(Market.symbol == symbol).first()
        if existing:
            # Update fields if they are different or null
            changed = False
            for k, v in data.items():
                if getattr(existing, k) != v:
                    setattr(existing, k, v)
                    changed = True
            
            # Update country_id if it's different
            if existing.country_id != resolved_country_id:
                existing.country_id = resolved_country_id
                changed = True
                
            if changed:
                updated += 1
        else:
            market_data = dict(data)
            market_data["country_id"] = resolved_country_id
            market = Market(**market_data)
            db.add(market)
            inserted += 1

    if inserted > 0 or updated > 0:
        db.commit()
        logger.info("Market seeder: inserted %d new assets, updated %d assets.", inserted, updated)

    # Automatically generate trading signals for any markets that do not have one
    from ..models.trading_signal_model import TradingSignal
    from ..services.signal_service import signal_service
    
    all_markets = db.query(Market).all()
    generated_count = 0
    for m in all_markets:
        has_signal = db.query(TradingSignal).filter(TradingSignal.market_id == m.id).first() is not None
        if not has_signal:
            try:
                signal_service.auto_generate_signal(db, m.id)
                generated_count += 1
            except Exception as e:
                logger.error("Market seeder: Failed to auto-generate signal for %s: %s", m.symbol, e)
                
    if generated_count > 0:
        logger.info("Market seeder: Generated %d new trading signals.", generated_count)

    return inserted
