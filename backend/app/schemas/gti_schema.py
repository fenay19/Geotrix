from pydantic import BaseModel
from datetime import datetime

class GTIScoreBase(BaseModel):
    current_score: float
    severity_category: str

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

class GTIHistoryCreate(GTIHistoryBase):
    timestamp: datetime

class GTIHistory(GTIHistoryBase):
    id: int
    timestamp: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
