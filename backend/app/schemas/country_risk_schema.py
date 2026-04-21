from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CountryRiskBase(BaseModel):
    country_code:str
    country_name:str
    risk_score:float
    color_code:str
    sector_exposure:Optional[dict]=None

class CountryRiskCreate(CountryRiskBase):
    pass
class CountryRisk(CountryRiskBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True