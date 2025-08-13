from datetime import datetime
from typing import List, Dict, Union
from uuid import UUID
from pydantic import BaseModel


class RecentCalculation(BaseModel):
    id: UUID                     # <- accept UUID directly
    type: str
    inputs: List[Union[int, float]]
    result: float
    created_at: datetime

    class Config:
        from_attributes = True  # allow model creation from SQLAlchemy objects


class ReportSummary(BaseModel):
    total_calculations: int
    counts_by_operation: Dict[str, int]  # e.g., {"addition": 2, "division": 1}
    average_operands: float              # rounded to 2 decimals in service
    recent_calculations: List[RecentCalculation]
