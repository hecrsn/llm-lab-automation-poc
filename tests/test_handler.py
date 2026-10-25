"""Minimal tests for the simulated handler."""

import pytest

from handler import SimulatedHandler, validate_step, InvalidStepError


def test_validate_step_accepts_valid_input():
    step = validate_step({"source": "A1", "destination": "B2", "volume_ul": 100})
    assert step.source == "A1"
    assert step.destination == "B2"
    assert step.volume_ul == 100.0


def test_validate_step_rejects_invalid_position():
    with pytest.raises(InvalidStepError):
        validate_step({"source": "a1", "destination": "B2", "volume_ul": 100})


def test_validate_step_rejects_negative_volume():
    with pytest.raises(InvalidStepError):
        validate_step({"source": "A1", "destination": "B2", "volume_ul": -5})


def test_handler_executes_steps():
    handler = SimulatedHandler()
    steps = [validate_step({"source": "A1", "destination": "B1", "volume_ul": 100})]
    handler.execute(steps)
    assert len(handler.executed) == 1