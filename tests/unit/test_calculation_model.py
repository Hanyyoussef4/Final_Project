import pytest
from app.models.calculation import Calculation

@pytest.mark.parametrize(
    "calc_type,inputs,expected",
    [
        ("addition",      [5, 7, 3, 10], 25),
        ("subtraction",   [10, 2],       8),
        ("multiplication",[2, 3, 4],     24),
        ("division",      [20, 5],       4),
    ],
)
def test_get_result(calc_type, inputs, expected):
    c = Calculation.create(calculation_type=calc_type, user_id="00000000-0000-0000-0000-000000000000", inputs=inputs)
    assert c.get_result() == expected
