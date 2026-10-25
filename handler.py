"""Simulated liquid handler with input validation."""

import re
from dataclasses import dataclass

POSITION_PATTERN = re.compile(r"^[A-Z]([1-9]|[1-9][0-9])$")


@dataclass
class Step:
    source: str
    destination: str
    volume_ul: float


class InvalidStepError(ValueError):
    """Raised when a step fails validation."""


def validate_step(raw: dict) -> Step:
    """Validate a single step and return a Step object."""
    try:
        source = raw["source"]
        destination = raw["destination"]
        volume = raw["volume_ul"]
    except KeyError as e:
        raise InvalidStepError(f"Missing field: {e}") from e

    if not isinstance(source, str) or not POSITION_PATTERN.match(source):
        raise InvalidStepError(f"Invalid source position: {source!r}")
    if not isinstance(destination, str) or not POSITION_PATTERN.match(destination):
        raise InvalidStepError(f"Invalid destination position: {destination!r}")
    if not isinstance(volume, (int, float)) or volume <= 0:
        raise InvalidStepError(f"Invalid volume: {volume!r}")

    return Step(source=source, destination=destination, volume_ul=float(volume))


class SimulatedHandler:
    """A stand-in for a real liquid handling system."""

    def __init__(self) -> None:
        self.executed: list[Step] = []

    def execute(self, steps: list[Step]) -> None:
        for step in steps:
            print(f"[HANDLER] Aspirate {step.volume_ul:g} µL from {step.source}")
            print(f"[HANDLER] Dispense {step.volume_ul:g} µL into {step.destination}")
            self.executed.append(step)
        print(f"[HANDLER] Run complete: {len(self.executed)} steps executed")