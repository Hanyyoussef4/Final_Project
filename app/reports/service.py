from dataclasses import dataclass
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.calculation import Calculation

@dataclass
class ReportSummary:
    total_calculations: int
    counts_by_operation: Dict[str, int]
    average_operands: float
    recent_calculations: List[Calculation]

def build_report_summary(db: Session, user_id: str) -> ReportSummary:
    """
    Build a summary report of calculations for a given user.
    """

    # Fetch all calculations for this user, most recent first
    calculations = (
        db.query(Calculation)
        .filter(Calculation.user_id == user_id)
        .order_by(Calculation.created_at.desc())
        .all()
    )

    total_count = len(calculations)

    # Count by operation type
    counts = {}
    total_operands = 0
    for calc in calculations:
        counts[calc.type] = counts.get(calc.type, 0) + 1
        total_operands += len(calc.inputs or [])

    avg_operands = total_operands / total_count if total_count > 0 else 0.0

    return ReportSummary(
        total_calculations=total_count,
        counts_by_operation=counts,
        average_operands=avg_operands,
        recent_calculations=calculations
    )
