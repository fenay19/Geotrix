import math
from pydantic import BaseModel, model_validator
from typing import Optional, List
from datetime import datetime

def clean_nan_inf_before(cls, data):
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                if k in cls.model_fields and not cls.model_fields[k].is_required():
                    data[k] = None
                else:
                    data[k] = 0.0
        return data
    else:
        obj_dict = {}
        for k in cls.model_fields.keys():
            if hasattr(data, k):
                v = getattr(data, k)
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    if not cls.model_fields[k].is_required():
                        obj_dict[k] = None
                    else:
                        obj_dict[k] = 0.0
                else:
                    obj_dict[k] = v
        return obj_dict

class MarketBase(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def clean_nan_inf(cls, data):
        return clean_nan_inf_before(cls, data)

    symbol: str
    name: Optional[str] = None
    price: float
    category: str
    asset_class: Optional[str] = None   # Stocks|ETFs|Forex|Crypto|Commodities|Bonds|Indices
    geo_sensitivity: Optional[float] = None  # 0.0-1.0
    is_global: bool = False
    country_id: Optional[int] = None
    currency: Optional[str] = "USD"
    currency_symbol: Optional[str] = "$"

class MarketCreate(MarketBase):
    pass

class MarketUpdate(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def clean_nan_inf(cls, data):
        return clean_nan_inf_before(cls, data)

    price: Optional[float] = None

class MarketHistoryBase(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def clean_nan_inf(cls, data):
        return clean_nan_inf_before(cls, data)

    market_id: int
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    timestamp: datetime

class MarketHistoryCreate(MarketHistoryBase):
    pass

class MarketHistory(MarketHistoryBase):
    id: int
    market_id: int

    class Config:
        from_attributes = True

class Market(MarketBase):
    id: int
    history: List[MarketHistory] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MarketWithSignal(BaseModel):
    """Lightweight market + latest signal summary for Signals list page."""
    @model_validator(mode="before")
    @classmethod
    def clean_nan_inf(cls, data):
        return clean_nan_inf_before(cls, data)

    id: int
    symbol: str
    name: Optional[str] = None
    price: Optional[float] = None
    asset_class: Optional[str] = None
    geo_sensitivity: Optional[float] = None
    latest_signal_type: Optional[str] = None
    latest_signal_confidence: Optional[float] = None
    latest_signal_id: Optional[int] = None

    class Config:
        from_attributes = True


class LocalMarketsResponse(BaseModel):
    country_assets: List[Market]
    fallback_assets: List[Market]
    market_context: dict[str, str]
