import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.calculation import Calculation
from app.reports.service import build_report_summary


@pytest.fixture
def sample_calculations(db_session: Session, test_user):
    """
    Creates a set of sample calculations for the given user.
    Uses fields matching your model: type (str), inputs (list), result (number).
    """
    now = datetime.utcnow()
    rows = [
        Calculation(
            user_id=test_user.id,
            type="addition",
            inputs=[1, 2, 3],
            result=6,
            created_at=now - timedelta(minutes=3),
        ),
        Calculation(
            user_id=test_user.id,
            type="subtraction",
            inputs=[10, 5],
            result=5,
            created_at=now - timedelta(minutes=2),
        ),
        Calculation(
            user_id=test_user.id,
            type="addition",
            inputs=[4, 4],
            result=8,
            created_at=now - timedelta(minutes=1),
        ),
    ]
    db_session.add_all(rows)
    db_session.commit()
    return rows


def test_build_report_summary_counts_and_average(db_session: Session, test_user, sample_calculations):
    summary = build_report_summary(db_session, test_user.id)

    assert summary.total_calculations == 3
    assert summary.counts_by_operation == {"addition": 2, "subtraction": 1}
    # Average operands: (3 + 2 + 2) / 3 = 2.33
    assert round(summary.average_operands, 2) == 2.33
    assert len(summary.recent_calculations) == 3

    # Most recent should be the 'addition' with inputs [4, 4]
    assert summary.recent_calculations[0].type == "addition"
    assert summary.recent_calculations[0].inputs == [4, 4]
