"""Minimal tests for the simulated handler."""

import pytest

from handler import SimulatedHandler, validate_step, InvalidStepError
from handler import expand_range, parse_position
from handler import execute_tool_call
from handler import ClarificationRequested
from instruction_validation import (
    validate_tool_call_location,
    validate_tool_call_volume,
)


def test_parse_position():
    assert parse_position("A1") == ("A", 1)
    assert parse_position("H12") == ("H", 12)


def test_parse_position_rejects_invalid():
    with pytest.raises(InvalidStepError):
        parse_position("a1")


def test_expand_range_single_column():
    wells = expand_range("A1", "C1")
    assert wells == ["A1", "B1", "C1"]


def test_expand_range_rectangle():
    wells = expand_range("A1", "C2")
    assert wells == ["A1", "A2", "B1", "B2", "C1", "C2"]


def test_expand_range_rejects_reversed():
    with pytest.raises(InvalidStepError):
        expand_range("C2", "A1")

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


def test_execute_tool_call_fill_wells():
    handler = SimulatedHandler()
    result = execute_tool_call(
        "fill_wells",
        {
            "range_start": "A1",
            "range_end": "C12",
            "source_location": "H1",
            "volume_ul": 100,
            "reagent": "Agonist A",
        },
        handler,
    )

    assert result.startswith("Success:")
    assert len(handler.operations) == 36
    assert all(operation["type"] == "fill" for operation in handler.operations)
    assert all(operation["source_location"] == "H1" for operation in handler.operations)


def test_execute_tool_call_aspirate_wells():
    handler = SimulatedHandler()
    result = execute_tool_call(
        "aspirate_wells",
        {"range_start": "A1", "range_end": "C12", "volume_ul": 200},
        handler,
    )

    assert result.startswith("Success:")
    assert len(handler.operations) == 36
    assert all(operation["type"] == "aspirate" for operation in handler.operations)


def test_execute_tool_call_unknown_tool():
    result = execute_tool_call("unknown_tool", {}, SimulatedHandler())

    assert result == "Error: unknown tool 'unknown_tool'."


def test_unstated_fill_volume_requests_clarification():
    instruction = (
        "Wells A1 bis C12 werden mit Agonist A befüllt, "
        "D1 bis F12 mit Agonist B. "
        "Sauge davor 200 µl aus allen Wells ab."
    )

    with pytest.raises(ClarificationRequested) as error:
        validate_tool_call_volume(
            instruction,
            "fill_wells",
            {"volume_ul": 1000},
        )

    assert "What volume" in error.value.question


def test_second_range_cannot_reuse_first_range_volume():
    instruction = (
        "Wells A1 bis C12 werden mit 50 µl Agonist A befüllt, "
        "D1 bis F12 mit Agonist B. "
        "Sauge davor 200 µl aus allen Wells ab."
    )

    validate_tool_call_volume(
        instruction,
        "fill_wells",
        {
            "range_start": "A1",
            "range_end": "C12",
            "volume_ul": 50,
            "reagent": "Agonist A",
        },
    )

    with pytest.raises(ClarificationRequested) as error:
        validate_tool_call_volume(
            instruction,
            "fill_wells",
            {
                "range_start": "D1",
                "range_end": "F12",
                "volume_ul": 50,
                "reagent": "Agonist B",
            },
        )

    assert "D1-F12 with Agonist B" in error.value.question


def test_volume_from_other_action_does_not_validate_fill():
    instruction = "Fill A1 to C12 with 50 µL of Agonist A, then aspirate 200 µL."

    with pytest.raises(ClarificationRequested):
        validate_tool_call_volume(
            instruction,
            "fill_wells",
            {"volume_ul": 200},
        )


def test_explicit_action_volume_is_accepted():
    validate_tool_call_volume(
        "Fill A1 to C12 with 100 µL of Agonist A.",
        "fill_wells",
        {"volume_ul": 100},
    )


def test_fill_reagent_requires_its_stated_range():
    instruction = (
        "Agonist A is in H1. Wells A1 bis C12 werden mit 50 µl Agonist A befüllt, "
        "D1 bis F12 mit Agonist B."
    )
    validate_tool_call_location(
        instruction,
        "fill_wells",
        {
            "range_start": "A1",
            "range_end": "C12",
            "source_location": "H1",
            "volume_ul": 50,
            "reagent": "Agonist A",
        },
    )

    with pytest.raises(ClarificationRequested) as error:
        validate_tool_call_location(
            instruction,
            "fill_wells",
            {
                "range_start": "D1",
                "range_end": "F12",
                "source_location": "H1",
                "volume_ul": 40,
                "reagent": "Agonist A",
            },
        )

    assert "Which well or range" in error.value.question


def test_fill_rejects_model_invented_location():
    instruction = "Agonist A is in H1. Fill 50 µL Agonist A."

    with pytest.raises(ClarificationRequested) as error:
        validate_tool_call_location(
            instruction,
            "fill_wells",
            {
                "range_start": "A1",
                "range_end": "C12",
                "source_location": "H1",
                "volume_ul": 50,
                "reagent": "Agonist A",
            },
        )

    assert "Which well or range" in error.value.question


def test_fill_rejects_missing_tool_location():
    with pytest.raises(ClarificationRequested):
        validate_tool_call_location(
            "Agonist A is in H1. Fill 50 µL Agonist A into A1 to C12.",
            "fill_wells",
            {
                "source_location": "H1",
                "volume_ul": 50,
                "reagent": "Agonist A",
            },
        )


def test_fill_requires_stated_reagent_source_location():
    instruction = "Fill 50 µL Agonist A into A1 to C12."

    with pytest.raises(ClarificationRequested) as error:
        validate_tool_call_location(
            instruction,
            "fill_wells",
            {
                "range_start": "A1",
                "range_end": "C12",
                "source_location": "H1",
                "volume_ul": 50,
                "reagent": "Agonist A",
            },
        )

    assert "Which source well contains Agonist A?" in error.value.question


def test_german_parenthetical_source_locations_are_recognized():
    instruction = (
        "Wells A1 bis C12 werden mit 50 µl Agonist A (H11)befüllt, "
        "D1 bis F12 mit 40 µl Agonist B (H12)."
    )

    validate_tool_call_location(
        instruction,
        "fill_wells",
        {
            "range_start": "A1",
            "range_end": "C12",
            "source_location": "H11",
            "volume_ul": 50,
            "reagent": "Agonist A",
        },
    )
    validate_tool_call_location(
        instruction,
        "fill_wells",
        {
            "range_start": "D1",
            "range_end": "F12",
            "source_location": "H12",
            "volume_ul": 40,
            "reagent": "Agonist B",
        },
    )


def test_dispense_rejects_model_invented_location():
    with pytest.raises(ClarificationRequested):
        validate_tool_call_location(
            "Agonist A is in H1. Dispense 50 µL of Agonist A.",
            "dispense",
            {
                "destination": "A1",
                "source_location": "H1",
                "volume_ul": 50,
                "reagent": "Agonist A",
            },
        )
    validate_tool_call_volume(
        "Add 100 µL of reagent to A1.",
        "dispense",
        {"volume_ul": 100},
    )