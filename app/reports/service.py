from sqlalchemy.orm import Session
from sqlalchemy import func, cast
from sqlalchemy.dialects.postgresql import JSONB
from app.models.calculation import Calculation
from app.schemas.report import ReportSummary, RecentCalculation


def build_report_summary(db: Session, user_id: str) -> ReportSummary:
    """
    Build a summary report of calculations for a given user.
    """
    # Total count of all calculations
    total_count = db.query(func.count(Calculation.id)).filter(
        Calculation.user_id == user_id
    ).scalar()

    # Count by operation type
    counts_by_operation = dict(
        db.query(
            Calculation.type,
            func.count(Calculation.id)
        )
        .filter(Calculation.user_id == user_id)
        .group_by(Calculation.type)
        .all()
    )

    # Average number of inputs (works with JSON)
    avg_inputs = db.query(
        func.avg(func.jsonb_array_length(cast(Calculation.inputs, JSONB)))
    ).filter(Calculation.user_id == user_id).scalar() or 0

    # Most recent 5 calculations
    recent_calcs = (
        db.query(Calculation)
        .filter(Calculation.user_id == user_id)
        .order_by(Calculation.created_at.desc())
        .limit(5)
        .all()
    )

    recent_calcs_schema = [
        RecentCalculation(
            id=calc.id,
            type=calc.type,
            inputs=calc.inputs,
            result=calc.result,
            created_at=calc.created_at
        )
        for calc in recent_calcs
    ]

    return ReportSummary(
        total_calculations=total_count,
        counts_by_operation=counts_by_operation,
        average_inputs=avg_inputs,
        recent_calculations=recent_calcs_schema
    )
