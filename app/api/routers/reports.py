from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_active_user  # FIXED: match existing code
from app.schemas.report import ReportSummary
from app.reports.service import build_report_summary

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
)


@router.get("/summary", response_model=ReportSummary)
def get_report_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user)  # FIXED
):
    """
    Returns a per-user calculation report summary.
    Requires authentication.
    """
    return build_report_summary(db, current_user.id)
