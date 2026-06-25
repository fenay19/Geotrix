from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import hashlib
from ...schemas.market_schema import Market, MarketCreate, MarketHistory, MarketHistoryCreate, MarketWithSignal, LocalMarketsResponse
from ...services.market_service import market_service
from ...dependencies import get_db, require_admin
from ...pipelines.market_pipeline import market_pipeline

router = APIRouter()


COUNTRY_CURRENCY_MAPPING = {
    "US": {"currency": "USD", "symbol": "$",   "rate": 1.0,    "premiums": {"GC=F": 1.0, "CL=F": 1.0, "SPY": 1.0}},
    "CN": {"currency": "CNY", "symbol": "¥",   "rate": 7.25,   "premiums": {"GC=F": 1.03, "CL=F": 1.05, "SPY": 1.0}},
    "RU": {"currency": "RUB", "symbol": "₽",   "rate": 90.5,   "premiums": {"GC=F": 0.95, "CL=F": 0.85, "SPY": 1.0}},
    "IN": {"currency": "INR", "symbol": "₹",   "rate": 83.5,   "premiums": {"GC=F": 1.12, "CL=F": 1.08, "SPY": 1.0}},
    "DE": {"currency": "EUR", "symbol": "€",   "rate": 0.92,   "premiums": {"GC=F": 1.02, "CL=F": 1.04, "SPY": 1.0}},
    "FR": {"currency": "EUR", "symbol": "€",   "rate": 0.92,   "premiums": {"GC=F": 1.02, "CL=F": 1.04, "SPY": 1.0}},
    "GB": {"currency": "GBP", "symbol": "£",   "rate": 0.79,   "premiums": {"GC=F": 1.01, "CL=F": 1.02, "SPY": 1.0}},
    "JP": {"currency": "JPY", "symbol": "¥",   "rate": 158.0,  "premiums": {"GC=F": 1.02, "CL=F": 1.05, "SPY": 1.0}},
    "IR": {"currency": "IRR", "symbol": "﷼",   "rate": 42000.0, "premiums": {"GC=F": 1.15, "CL=F": 0.70, "SPY": 1.0}},
    "IL": {"currency": "ILS", "symbol": "₪",   "rate": 3.75,   "premiums": {"GC=F": 1.04, "CL=F": 1.05, "SPY": 1.0}},
    "SA": {"currency": "SAR", "symbol": "ر.س", "rate": 3.75,   "premiums": {"GC=F": 1.05, "CL=F": 0.98, "SPY": 1.0}},
    "UA": {"currency": "UAH", "symbol": "₴",   "rate": 40.5,   "premiums": {"GC=F": 1.08, "CL=F": 1.12, "SPY": 1.0}},
    "AE": {"currency": "AED", "symbol": "د.إ",  "rate": 3.67,   "premiums": {"GC=F": 1.04, "CL=F": 1.00, "SPY": 1.0}},
    "CA": {"currency": "CAD", "symbol": "C$",  "rate": 1.37,   "premiums": {"GC=F": 1.02, "CL=F": 1.01, "SPY": 1.0}},
    "AU": {"currency": "AUD", "symbol": "A$",  "rate": 1.50,   "premiums": {"GC=F": 1.02, "CL=F": 1.02, "SPY": 1.0}},
    "NZ": {"currency": "NZD", "symbol": "NZ$", "rate": 1.63,   "premiums": {"GC=F": 1.02, "CL=F": 1.02, "SPY": 1.0}},
    "CH": {"currency": "CHF", "symbol": "Fr.", "rate": 0.89,   "premiums": {"GC=F": 1.01, "CL=F": 1.01, "SPY": 1.0}},
    "BR": {"currency": "BRL", "symbol": "R$",  "rate": 5.40,   "premiums": {"GC=F": 1.05, "CL=F": 1.05, "SPY": 1.0}},
    "TR": {"currency": "TRY", "symbol": "₺",   "rate": 32.50,  "premiums": {"GC=F": 1.08, "CL=F": 1.06, "SPY": 1.0}},
    "ZA": {"currency": "ZAR", "symbol": "R",   "rate": 18.20,  "premiums": {"GC=F": 1.06, "CL=F": 1.06, "SPY": 1.0}},
    "KR": {"currency": "KRW", "symbol": "₩",   "rate": 1380.0, "premiums": {"GC=F": 1.03, "CL=F": 1.05, "SPY": 1.0}},
    "MX": {"currency": "MXN", "symbol": "$",   "rate": 18.50,  "premiums": {"GC=F": 1.04, "CL=F": 1.03, "SPY": 1.0}},
    "SG": {"currency": "SGD", "symbol": "S$",  "rate": 1.35,   "premiums": {"GC=F": 1.02, "CL=F": 1.02, "SPY": 1.0}},
    "HK": {"currency": "HKD", "symbol": "HK$", "rate": 7.80,   "premiums": {"GC=F": 1.01, "CL=F": 1.02, "SPY": 1.0}},
    "TW": {"currency": "TWD", "symbol": "NT$", "rate": 32.30,  "premiums": {"GC=F": 1.03, "CL=F": 1.05, "SPY": 1.0}},
    "DK": {"currency": "DKK", "symbol": "kr.", "rate": 6.95,   "premiums": {"GC=F": 1.02, "CL=F": 1.03, "SPY": 1.0}},
    "GL": {"currency": "DKK", "symbol": "kr.", "rate": 6.95,   "premiums": {"GC=F": 1.03, "CL=F": 1.03, "SPY": 1.0}},
}

def get_deterministic_country_config(country_code: Optional[str]) -> dict:
    code = (country_code or "US").upper().strip()
    if code in COUNTRY_CURRENCY_MAPPING:
        return COUNTRY_CURRENCY_MAPPING[code]
    
    # Stable hashing based on MD5 of country code
    h_bytes = hashlib.md5(code.encode('utf-8')).digest()
    val1 = int.from_bytes(h_bytes[:4], 'big')
    val2 = int.from_bytes(h_bytes[4:8], 'big')
    val3 = int.from_bytes(h_bytes[8:12], 'big')
    
    # Pseudo-currency formatting
    currency = f"{code}Cur"
    symbol = f"{code}$"
    
    # Rate between 1.5 and 150.0
    rate = round(1.5 + (val1 % 14850) / 100.0, 2)
    # Gold premium between 1.00 and 1.15
    gold_premium = round(1.0 + (val2 % 16) / 100.0, 2)
    # Oil premium between 0.90 and 1.10
    oil_premium = round(0.90 + (val3 % 21) / 100.0, 2)
    
    return {
        "currency": currency,
        "symbol": symbol,
        "rate": rate,
        "premiums": {
            "GC=F": gold_premium,
            "CL=F": oil_premium,
            "SPY": 1.0
        }
    }

def adjust_market_for_country(market, country_code: Optional[str]):
    cfg = get_deterministic_country_config(country_code)
    rate = cfg["rate"]
    premium = cfg["premiums"].get(market.symbol, 1.0)
    
    base_price = market.price if market.price is not None else 0.0
    local_price = round(base_price * rate * premium, 2)
    
    return {
        "id": market.id,
        "symbol": market.symbol,
        "name": market.name,
        "price": local_price,
        "category": market.category,
        "asset_class": market.asset_class,
        "geo_sensitivity": market.geo_sensitivity,
        "is_global": market.is_global,
        "country_id": market.country_id,
        "currency": cfg["currency"],
        "currency_symbol": cfg["symbol"],
        "created_at": market.created_at,
        "updated_at": market.updated_at,
        "history": []
    }

def adjust_market_detail_for_country(market, country_code: Optional[str]):
    cfg = get_deterministic_country_config(country_code)
    rate = cfg["rate"]
    premium = cfg["premiums"].get(market.symbol, 1.0)
    
    base_price = market.price if market.price is not None else 0.0
    local_price = round(base_price * rate * premium, 2)
    
    adjusted_history = []
    for h in market.history:
        h_open = h.open if h.open is not None else 0.0
        h_high = h.high if h.high is not None else 0.0
        h_low = h.low if h.low is not None else 0.0
        h_close = h.close if h.close is not None else 0.0
        
        adjusted_history.append({
            "id": h.id,
            "market_id": h.market_id,
            "open": round(h_open * rate * premium, 2),
            "high": round(h_high * rate * premium, 2),
            "low": round(h_low * rate * premium, 2),
            "close": round(h_close * rate * premium, 2),
            "volume": h.volume,
            "timestamp": h.timestamp,
        })
        
    return {
        "id": market.id,
        "symbol": market.symbol,
        "name": market.name,
        "price": local_price,
        "category": market.category,
        "asset_class": market.asset_class,
        "geo_sensitivity": market.geo_sensitivity,
        "is_global": market.is_global,
        "country_id": market.country_id,
        "currency": cfg["currency"],
        "currency_symbol": cfg["symbol"],
        "created_at": market.created_at,
        "updated_at": market.updated_at,
        "history": adjusted_history
    }



@router.get("/", response_model=List[Market])
def read_markets(db: Session = Depends(get_db)):
    return market_service.get_markets(db)


@router.get("/global", response_model=List[Market])
def get_global_assets(limit: int = 5, db: Session = Depends(get_db)):
    return market_service.get_global_assets(db, limit)


@router.get("/local/{country_id}", response_model=LocalMarketsResponse)
def get_local_assets(country_id: int, country_code: Optional[str] = None, db: Session = Depends(get_db)):
    from ...models.country_risk_model import CountryRisk
    from ...models.market_model import Market as MarketModel
    
    country = db.query(CountryRisk).filter(CountryRisk.id == country_id).first()
    
    # Resolve country_code if not provided
    if not country_code and country:
        country_code = country.country_code
    
    if not country_code:
        country_code = "US"
        
    if country:
        # Get country-specific assets
        country_assets = db.query(MarketModel).filter(MarketModel.country_id == country_id).all()
        country_name = country.country_name
        energy_pct = country.sector_exposure.get("Energy") if country.sector_exposure else None
    else:
        # Untracked/fallback countries (like Antarctica or other non-seeded regions)
        country_assets = []
        country_name = f"Region ({country_code})"
        energy_pct = None
        
    # Get fallback assets (SPY, GC=F, CL=F)
    symbols_order = ["SPY", "GC=F", "CL=F"]
    fallback_assets_dict = {m.symbol: m for m in db.query(MarketModel).filter(MarketModel.symbol.in_(symbols_order)).all()}
    fallback_assets = [fallback_assets_dict[sym] for sym in symbols_order if sym in fallback_assets_dict]
    
    # Dynamically generate market_context dict
    spy_context = f"Global Equity Indicator: Displays overall market sentiment. Shows how {country_name}'s economy correlates with global capital flows."
    golds_context = f"Geopolitical Safe Haven: Displays Gold price trends. High global risk scores drive capital into safe havens, impacting trade value and currency pressure for {country_name}."
    
    if energy_pct is not None:
        oil_context = f"Energy Benchmark: Tracks global oil prices. Crucial for {country_name} due to its estimated {energy_pct}% energy sector exposure."
    else:
        oil_context = f"Energy Benchmark: Tracks global oil prices. Relevant because energy costs influence trade balances, inflation, and supply chains in {country_name}."

    market_context = {
        "SPY": spy_context,
        "GC=F": golds_context,
        "CL=F": oil_context
    }
    
    # Apply country adjustments
    adjusted_country_assets = [adjust_market_for_country(m, country_code) for m in country_assets]
    adjusted_fallback_assets = [adjust_market_for_country(m, country_code) for m in fallback_assets]
    
    return {
        "country_assets": adjusted_country_assets,
        "fallback_assets": adjusted_fallback_assets,
        "market_context": market_context
    }


@router.post("/", response_model=Market, status_code=201)
def create_market(market_in: MarketCreate, db: Session = Depends(get_db)):
    return market_service.create_market(db, market_in)


@router.get("/all-with-signals", response_model=List[MarketWithSignal])
def get_all_markets_with_signals(db: Session = Depends(get_db)):
    """Returns all markets joined with their latest signal — single call for the Signals page list."""
    from ...models.market_model import Market as MarketModel
    from ...models.trading_signal_model import TradingSignal
    from sqlalchemy import desc, func

    # 1. Fetch the latest signal per market using subquery join
    subq = (
        db.query(
            TradingSignal.market_id,
            func.max(TradingSignal.created_at).label("max_created")
        )
        .group_by(TradingSignal.market_id)
        .subquery()
    )

    latest_signals = (
        db.query(TradingSignal)
        .join(subq, (TradingSignal.market_id == subq.c.market_id) &
                    (TradingSignal.created_at == subq.c.max_created))
        .all()
    )

    # 2. Map market_id to its latest signal
    signal_by_market = {sig.market_id: sig for sig in latest_signals}

    # 3. Build results list
    markets = db.query(MarketModel).all()
    results = []
    for m in markets:
        latest = signal_by_market.get(m.id)
        results.append(MarketWithSignal(
            id=m.id,
            symbol=m.symbol,
            name=m.name,
            price=m.price,
            asset_class=m.asset_class,
            geo_sensitivity=m.geo_sensitivity,
            latest_signal_type=latest.signal_type if latest else None,
            latest_signal_confidence=latest.confidence if latest else None,
            latest_signal_id=latest.id if latest else None,
        ))
    return results


@router.get("/{symbol}", response_model=Market)
def read_market(symbol: str, country_code: Optional[str] = None, db: Session = Depends(get_db)):
    market = market_service.get_market(db, symbol)
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    if country_code:
        return adjust_market_detail_for_country(market, country_code)
    return market


@router.post("/history", response_model=MarketHistory, status_code=201)
def add_market_history(history_in: MarketHistoryCreate, db: Session = Depends(get_db)):
    return market_service.add_market_history(db, history_in)


@router.post("/sync")
def sync_market_data(history_days: int = 180, db: Session = Depends(get_db), admin=Depends(require_admin)):
    """
    Triggers the Market Data Pipeline:
    - Fetches live price quotes from Finnhub for all registered markets.
    - Fetches and stores historical OHLC candle data for the past N days.
    Returns a summary of prices updated and candles inserted.
    """
    return market_pipeline.sync_all_markets(db, history_days=history_days)


@router.get("/by-class/{asset_class}", response_model=List[Market])
def get_markets_by_class(asset_class: str, db: Session = Depends(get_db)):
    """Filter markets by asset class (Stocks, ETFs, Forex, Crypto, Commodities, Bonds, Indices)."""
    from ...models.market_model import Market as MarketModel
    return db.query(MarketModel).filter(
        MarketModel.asset_class.ilike(asset_class)
    ).all()
