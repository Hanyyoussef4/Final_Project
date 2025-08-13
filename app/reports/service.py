from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.calculation import Calculation

def build_report_summary(db: Session, user_id: str):
    """
    Build a summary report of calculations for a given user.

    Args:
        db (Session): SQLAlchemy session
        user_id (str): User's ID

    Returns:
        dict: Summary of calculation statistics
    """
    total_count = db.query(func.count(Calculation.id)).filter(
        Calculation.user_id == user_id
    ).scalar()

    by_type = (
        db.query(
            Calculation.type,
            func.count(Calculation.id)
        )
        .filter(Calculation.user_id == user_id)
        .group_by(Calculation.type)
        .all()
    )

    return {
        "total_calculations": total_count,
        "by_type": {calc_type: count for calc_type, count in by_type}
    }
