from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.calculation import Calculation
from app.schemas.report import ReportSummary, RecentCalculation  # make sure these imports exist

def build_report_summary(db: Session, user_id: str) -> ReportSummary:
    total_count = db.query(func.count(Calculation.id)).filter(
        Calculation.user_id == user_id
    ).scalar()

    counts_by_operation = dict(
        db.query(
            Calculation.type,
            func.count(Calculation.id)
        )
        .filter(Calculation.user_id == user_id)
        .group_by(Calculation.type)
        .all()
    )

    avg_operands = db.query(
        func.avg(func.array_length(Calculation.inputs, 1))
    ).filter(Calculation.user_id == user_id).scalar() or 0

    recent_calcs = db.query(Calculation).filter(
        Calculation.user_id == user_id
    ).order_by(Calculation.created_at.desc()).limit(5).all()

    recent_calcs_schema = [
        RecentCalculation(
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
        average_operands=avg_operands,
        recent_calculations=recent_calcs_schema
    )
