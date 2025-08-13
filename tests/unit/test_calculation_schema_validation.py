# tests/unit/test_calculation_schema_validation.py
import uuid
import pytest
from app.schemas.calculation import CalculationCreate

def test_calculation_create_valid():
    c = CalculationCreate(
        type="Addition",       # schema will normalize to lowercase
        inputs=[1, 2, 3],
        user_id=uuid.uuid4(),  # UUID object
    )
    assert c.type == "addition"  # normalized value
    assert len(c.inputs) == 3

def test_calculation_create_rejects_empty_inputs():
    with pytest.raises(Exception):
        CalculationCreate(
            type="Addition",
            inputs=[],
            user_id=str(uuid.uuid4()),
        )
