"""Simulated liquid handler with input validation and range support."""

import re
from dataclasses import dataclass

POSITION_PATTERN = re.compile(r"^([A-Z])([1-9][0-9]?)$")


@dataclass
class Step:
    source: str
    destination: str
    volume_ul: float


class InvalidStepError(ValueError):
    """Raised when a step fails validation."""


class ClarificationRequested(Exception):
    """Raised when the LLM asks the user for clarification."""

    def __init__(self, question: str, reason: str) -> None:
        super().__init__(f"{question} (reason: {reason})")
        self.question = question
        self.reason = reason


def parse_position(position: str) -> tuple[str, int]:
    """Parse 'A1' -> ('A', 1). Raises InvalidStepError on bad input."""
    if not isinstance(position, str):
        raise InvalidStepError(f"Position must be a string: {position!r}")
    match = POSITION_PATTERN.match(position)
    if not match:
        raise InvalidStepError(f"Invalid position: {position!r}")
    return match.group(1), int(match.group(2))


def expand_range(start: str, end: str) -> list[str]:
    """Expand a rectangular range like A1..C2 into ['A1','A2','B1','B2','C1','C2']."""
    start_row, start_col = parse_position(start)
    end_row, end_col = parse_position(end)
    if start_row > end_row:
        raise InvalidStepError(f"Range start row '{start_row}' > end row '{end_row}'")
    if start_col > end_col:
        raise InvalidStepError(f"Range start column {start_col} > end column {end_col}")
    wells = []
    for row_ord in range(ord(start_row), ord(end_row) + 1):
        for col in range(start_col, end_col + 1):
            wells.append(f"{chr(row_ord)}{col}")
    return wells


def validate_step(raw: dict) -> Step:
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
        self.executed: list[Step] = []       # backward-compat: transfers only
        self.operations: list[dict] = []     # full operation log

    def execute(self, steps: list[Step]) -> None:
        for step in steps:
            print(f"[HANDLER] Aspirate {step.volume_ul:g} µL from {step.source}")
            print(f"[HANDLER] Dispense {step.volume_ul:g} µL into {step.destination}")
            self.executed.append(step)
            self.operations.append({
                "type": "transfer",
                "source": step.source,
                "destination": step.destination,
                "volume_ul": step.volume_ul,
            })

    def aspirate(self, source: str, volume_ul: float) -> None:
        print(f"[HANDLER] Aspirate {volume_ul:g} µL from {source} (waste)")
        self.operations.append({"type": "aspirate", "source": source, "volume_ul": volume_ul})

    def dispense(
        self,
        destination: str,
        volume_ul: float,
        reagent: str = "liquid",
        source_location: str | None = None,
    ) -> None:
        source_text = f" from {source_location}" if source_location else ""
        print(f"[HANDLER] Dispense {volume_ul:g} µL of {reagent}{source_text} into {destination}")
        self.operations.append({
            "type": "dispense", "destination": destination,
            "volume_ul": volume_ul, "reagent": reagent,
            "source_location": source_location,
        })

    def fill_wells(
        self,
        wells: list[str],
        volume_ul: float,
        reagent: str,
        source_location: str | None = None,
    ) -> None:
        source_text = f" from {source_location}" if source_location else ""
        print(f"[HANDLER] Fill {len(wells)} wells ({wells[0]}..{wells[-1]}) "
              f"with {volume_ul:g} µL of {reagent}{source_text}")
        for well in wells:
            self.operations.append({
                "type": "fill", "destination": well,
                "volume_ul": volume_ul, "reagent": reagent,
                "source_location": source_location,
            })

    def aspirate_wells(self, wells: list[str], volume_ul: float) -> None:
        print(f"[HANDLER] Aspirate {volume_ul:g} µL from each of {len(wells)} wells "
              f"({wells[0]}..{wells[-1]})")
        for well in wells:
            self.operations.append({
                "type": "aspirate", "source": well, "volume_ul": volume_ul,
            })


def execute_tool_call(name: str, arguments: dict, handler: SimulatedHandler) -> str:
    """Execute a single tool call and return a result message for the LLM."""

    if name == "transfer_liquid":
        try:
            step = validate_step(arguments)
        except InvalidStepError as e:
            return f"Error: {e}"
        handler.execute([step])
        return f"Success: transferred {step.volume_ul:g} µL from {step.source} to {step.destination}."

    if name == "aspirate":
        try:
            source = arguments["source"]
            volume = float(arguments["volume_ul"])
            parse_position(source)
            if volume <= 0:
                raise InvalidStepError(f"Invalid volume: {volume}")
        except (KeyError, TypeError, ValueError, InvalidStepError) as e:
            return f"Error: {e}"
        handler.aspirate(source, volume)
        return f"Success: aspirated {volume:g} µL from {source} (waste)."

    if name == "dispense":
        try:
            destination = arguments["destination"]
            source_location = arguments["source_location"]
            volume = float(arguments["volume_ul"])
            parse_position(destination)
            parse_position(source_location)
            if volume <= 0:
                raise InvalidStepError(f"Invalid volume: {volume}")
        except (KeyError, TypeError, ValueError, InvalidStepError) as e:
            return f"Error: {e}"
        reagent = arguments["reagent"]
        handler.dispense(destination, volume, reagent, source_location)
        return (
            f"Success: dispensed {volume:g} µL of {reagent} from "
            f"{source_location} into {destination}."
        )

    if name == "fill_wells":
        try:
            start = arguments["range_start"]
            end = arguments["range_end"]
            source_location = arguments["source_location"]
            volume = float(arguments["volume_ul"])
            reagent = arguments["reagent"]
            wells = expand_range(start, end)
            parse_position(source_location)
            if volume <= 0:
                raise InvalidStepError(f"Invalid volume: {volume}")
        except (KeyError, TypeError, ValueError, InvalidStepError) as e:
            return f"Error: {e}"
        handler.fill_wells(wells, volume, reagent, source_location)
        return (
            f"Success: filled {len(wells)} wells ({start}..{end}) with "
            f"{volume:g} µL of {reagent} from {source_location}."
        )

    if name == "aspirate_wells":
        try:
            start = arguments["range_start"]
            end = arguments["range_end"]
            volume = float(arguments["volume_ul"])
            wells = expand_range(start, end)
            if volume <= 0:
                raise InvalidStepError(f"Invalid volume: {volume}")
        except (KeyError, TypeError, ValueError, InvalidStepError) as e:
            return f"Error: {e}"
        handler.aspirate_wells(wells, volume)
        return f"Success: aspirated {volume:g} µL from each of {len(wells)} wells ({start}..{end})."

    if name == "request_clarification":
        raise ClarificationRequested(
            question=arguments.get("question", "Could you clarify?"),
            reason=arguments.get("reason", "unspecified"),
        )

    return f"Error: unknown tool '{name}'."