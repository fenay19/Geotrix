from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CountryRiskBase(BaseModel):
    country_code: str
    country_name: str
    risk_score: float
    color_code: str

class CountryRiskCreate(CountryRiskBase):
    pass

class CountryRisk(CountryRiskBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
