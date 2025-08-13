from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.reports.service import build_report_summary

router = APIRouter()

@router.get(
    "/summary",
    summary="Get calculation summary",
    description="JWT-secured endpoint returning calculation statistics."
)
def get_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve a summary of calculations for the authenticated user.
    """
    return build_report_summary(db, current_user.id)
