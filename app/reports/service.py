from __future__ import annotations

from typing import Dict, List, Any
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.models.calculation import Calculation
from app.schemas.report import ReportSummary, RecentCalculation


def _count_operands(raw_inputs: Any) -> int:
    """
    Your Calculation.inputs is stored as a JSON array (list) in the DB.
    But we also tolerate strings like '1,2,3' just in case.
    """
    if raw_inputs is None:
        return 0
    if isinstance(raw_inputs, (list, tuple)):
        return len(raw_inputs)
    if isinstance(raw_inputs, str):
        return len([p.strip() for p in raw_inputs.split(",") if p.strip()])
    return 0


def build_report_summary(db: Session, user_id) -> ReportSummary:
    """
    Aggregate per-user calculation stats based on your model fields:
      - total calculations
      - counts by operation (by `type`)
      - average operands per calculation (length of `inputs`)
      - 5 most recent calculations
    Returns a ReportSummary Pydantic model.
    """

    # --- total ---
    total_calculations: int = db.scalar(
        select(func.count()).select_from(Calculation).where(Calculation.user_id == user_id)
    ) or 0

    # --- counts by operation (type) ---
    op_rows = db.execute(
        select(Calculation.type, func.count())
        .where(Calculation.user_id == user_id)
        .group_by(Calculation.type)
    ).all()
    counts_by_operation: Dict[str, int] = {op: int(cnt) for op, cnt in op_rows}

    # --- average operands ---
    inputs_rows = db.execute(
        select(Calculation.inputs).where(Calculation.user_id == user_id)
    ).scalars().all()

    total_operands = sum(_count_operands(v) for v in inputs_rows)
    average_operands = (total_operands / total_calculations) if total_calculations else 0.0
    # normalize to two decimals for presentation
    average_operands = float(f"{average_operands:.2f}")

    # --- recent 5 calculations (newest first) ---
    recent_rows = db.execute(
        select(Calculation)
        .where(Calculation.user_id == user_id)
        .order_by(desc(Calculation.created_at))
        .limit(5)
    ).scalars().all()

    # Map to schema
    recent_calculations = [RecentCalculation.model_validate(row) for row in recent_rows]

    return ReportSummary(
        total_calculations=int(total_calculations),
        counts_by_operation=counts_by_operation,
        average_operands=average_operands,
        recent_calculations=recent_calculations,
    )
