from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional, Dict

class GTIScoreBase(BaseModel):
    current_score: float
    severity_category: str
    # breakdown can hold floats (pillar scores) AND nested dicts
    # (event_counts, pillar_priors) so we use Dict[str, Any].
    breakdown: Optional[Dict[str, Any]] = None

class GTIScoreCreate(GTIScoreBase):
    pass

class GTIScore(GTIScoreBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class GTIHistoryBase(BaseModel):
    score: float
    gti_id: Optional[int] = None
    breakdown: Optional[Dict[str, Any]] = None

class GTIHistoryCreate(GTIHistoryBase):
    timestamp: datetime

class GTIHistory(GTIHistoryBase):
    id: int
    timestamp: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
