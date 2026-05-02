from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Optional

class SignalBase(BaseModel):
    market_id: int
    event_id: Optional[int] = None
    signal_type: Literal["BUY", "SELL", "HOLD"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    uncertainty: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    bullish_strength: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    bearish_strength: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    entry_price: Optional[float] = Field(default=None, ge=0.0)
    stop_loss: Optional[float] = Field(default=None, ge=0.0)
    target_price: Optional[float] = Field(default=None, ge=0.0)
    risk_reward_ratio: Optional[float] = Field(default=None, ge=0.0)
    signal_strength: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    atr: Optional[float] = Field(default=None, ge=0.0)
    max_position_size: Optional[float] = Field(default=None, ge=0.0)
    volatility_level: Optional[Literal["Low", "Medium", "High"]] = None
    reasoning: Optional[str] = None
    risk_factors: Optional[list] = None
    tags: Optional[list] = None
    # ── Reliability Metrics ──────────────────────────────────────────
    signal_accuracy: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    win_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    annual_reliability_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    triggering_event: Optional[str] = None

class SignalCreate(SignalBase):
    pass

class Signal(SignalBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SignalWithMarket(Signal):
    """Signal enriched with market info for the Signals list/detail page."""
    market_symbol: Optional[str] = None
    market_name: Optional[str] = None
    market_price: Optional[float] = None
    market_asset_class: Optional[str] = None
    market_geo_sensitivity: Optional[float] = None

    class Config:
        from_attributes = True
