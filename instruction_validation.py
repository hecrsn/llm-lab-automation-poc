"""Validate that tool-call arguments are grounded in the user's instruction."""

import re
from decimal import Decimal, InvalidOperation

from handler import ClarificationRequested

VOLUME_PATTERN = re.compile(
    r"(?<!\w)(\d+(?:[.,]\d+)?)\s*"
    r"(µl|μl|ul|microliters?|ml|milliliters?|nl|nanoliters?)\b",
    re.IGNORECASE,
)

ACTION_PATTERNS = {
    "transfer": re.compile(
        r"\b(?:transfer\w*|move\w*|übertrag\w*|verschieb\w*)\b", re.IGNORECASE
    ),
    "aspirate": re.compile(
        r"\b(?:aspirat\w*|saug\w*|absaug\w*|remov\w*)\b", re.IGNORECASE
    ),
    "fill": re.compile(
        r"\b(?:fill\w*|befüll\w*|befull\w*|dispens\w*|add\w*|geb\w*)\b",
        re.IGNORECASE,
    ),
}

TOOL_ACTIONS = {
    "transfer_liquid": "transfer",
    "aspirate": "aspirate",
    "aspirate_wells": "aspirate",
    "dispense": "fill",
    "fill_wells": "fill",
}

UNIT_TO_MICROLITERS = {
    "µl": Decimal("1"),
    "μl": Decimal("1"),
    "ul": Decimal("1"),
    "microliter": Decimal("1"),
    "microliters": Decimal("1"),
    "ml": Decimal("1000"),
    "milliliter": Decimal("1000"),
    "milliliters": Decimal("1000"),
    "nl": Decimal("0.001"),
    "nanoliter": Decimal("0.001"),
    "nanoliters": Decimal("0.001"),
}

WELL_RANGE_PATTERN = re.compile(
    r"\b([A-Z][1-9][0-9]?)\s*(?:bis|to|through|[-–—])\s*"
    r"([A-Z][1-9][0-9]?)\b",
    re.IGNORECASE,
)
WELL_POSITION_PATTERN = re.compile(r"\b[A-Z][1-9][0-9]?\b", re.IGNORECASE)


def _clarification_question(name: str, arguments: dict) -> str:
    target = name
    if "range_start" in arguments and "range_end" in arguments:
        target = f"{arguments['range_start']}-{arguments['range_end']}"
    elif "destination" in arguments:
        target = str(arguments["destination"])

    reagent = arguments.get("reagent")
    if reagent:
        target = f"{target} with {reagent}"
    return f"What volume in µL should be used for {target}?"


def _location_question(name: str, arguments: dict) -> str:
    reagent = arguments.get("reagent")
    if reagent:
        return f"Which well or range should {reagent} be used in?"
    return f"What well or range should be used for {name}?"


def _source_location_question(arguments: dict) -> str:
    reagent = arguments.get("reagent", "the reagent")
    return f"Which source well contains {reagent}? Please provide a well such as H1."


def validate_tool_call_location(
    user_input: str, name: str, arguments: dict
) -> None:
    """Reject fill locations or reagent-to-location pairings absent from the request."""
    if name not in {"fill_wells", "dispense"}:
        return

    reagent = arguments.get("reagent")
    if not isinstance(reagent, str) or not reagent.strip():
        raise ClarificationRequested(
            question=f"What reagent should be used for {name}?",
            reason="The instruction does not specify the reagent for this fill.",
        )

    source_location = arguments.get("source_location")
    if not isinstance(source_location, str) or not WELL_POSITION_PATTERN.fullmatch(
        source_location
    ):
        raise ClarificationRequested(
            question=_source_location_question(arguments),
            reason="The instruction does not specify a valid source well for this reagent.",
        )

    source_is_stated = False
    source_reference = re.compile(
        rf"\b(?:from|at|in|source(?:\s+well)?(?:\s+at)?|"
        rf"stock(?:\s+well)?(?:\s+at)?)\s+{re.escape(source_location)}\b",
        re.IGNORECASE,
    )
    parenthetical_source = re.compile(
        rf"\b{re.escape(reagent)}\s*\(\s*{re.escape(source_location)}\s*\)",
        re.IGNORECASE,
    )
    for clause in re.split(r"[,;.!?\n]+", user_input):
        if (
            re.search(rf"\b{re.escape(reagent)}\b", clause, re.IGNORECASE)
            and (
                source_reference.search(clause)
                or parenthetical_source.search(clause)
            )
        ):
            source_is_stated = True
            break
    if not source_is_stated:
        raise ClarificationRequested(
            question=_source_location_question(arguments),
            reason=(
                f"The instruction does not state that {source_location} "
                f"contains {reagent}."
            ),
        )

    if name == "fill_wells":
        range_start = arguments.get("range_start")
        range_end = arguments.get("range_end")
        if not isinstance(range_start, str) or not isinstance(range_end, str):
            raise ClarificationRequested(
                question=_location_question(name, arguments),
                reason="The instruction does not specify a location for this fill.",
            )
        range_pair = (range_start.upper(), range_end.upper())

        for clause in re.split(r"[,;.!?\n]+", user_input):
            stated_ranges = {
                (match.group(1).upper(), match.group(2).upper())
                for match in WELL_RANGE_PATTERN.finditer(clause)
            }
            if (
                range_pair in stated_ranges
                and re.search(rf"\b{re.escape(reagent)}\b", clause, re.IGNORECASE)
            ):
                return

        raise ClarificationRequested(
            question=_location_question(name, arguments),
            reason=(
                f"The instruction does not associate {reagent} with "
                f"the range {range_start}-{range_end}."
            ),
        )

    destination = arguments.get("destination")
    if not isinstance(destination, str):
        raise ClarificationRequested(
            question=_location_question(name, arguments),
            reason="The instruction does not specify a location for this fill.",
        )
    for clause in re.split(r"[,;.!?\n]+", user_input):
        stated_positions = {
            match.group(0).upper()
            for match in WELL_POSITION_PATTERN.finditer(clause)
        }
        if (
            destination.upper() in stated_positions
            and re.search(rf"\b{re.escape(reagent)}\b", clause, re.IGNORECASE)
        ):
            return

    raise ClarificationRequested(
        question=_location_question(name, arguments),
        reason=(
            f"The instruction does not associate {reagent} with "
            f"the location {destination}."
        ),
    )


def validate_tool_call_volume(
    user_input: str, name: str, arguments: dict
) -> None:
    """Reject tool volumes that are not explicitly tied to that action."""
    if name not in TOOL_ACTIONS:
        return

    try:
        requested_volume = Decimal(str(arguments["volume_ul"]))
    except (KeyError, InvalidOperation, ValueError):
        raise ClarificationRequested(
            question=_clarification_question(name, arguments),
            reason="The tool call has no valid volume specified by the instruction.",
        ) from None

    if not requested_volume.is_finite():
        raise ClarificationRequested(
            question=_clarification_question(name, arguments),
            reason="The tool call has no valid volume specified by the instruction.",
        )

    expected_action = TOOL_ACTIONS[name]
    clauses = re.split(r"[,;.!?\n]+", user_input)
    target_clauses = []
    range_start = arguments.get("range_start")
    range_end = arguments.get("range_end")
    if isinstance(range_start, str) and isinstance(range_end, str):
        target_clauses = [
            clause
            for clause in clauses
            if re.search(rf"\b{re.escape(range_start)}\b", clause, re.IGNORECASE)
            and re.search(rf"\b{re.escape(range_end)}\b", clause, re.IGNORECASE)
        ]

    candidate_clauses = target_clauses or re.split(r"[.!?;\n]+", user_input)
    for sentence in candidate_clauses:
        action_matches = [
            (match.start(), match.end(), action)
            for action, pattern in ACTION_PATTERNS.items()
            for match in pattern.finditer(sentence)
        ]

        for volume_match in VOLUME_PATTERN.finditer(sentence):
            amount = Decimal(volume_match.group(1).replace(",", "."))
            unit = volume_match.group(2).lower()
            stated_volume = amount * UNIT_TO_MICROLITERS[unit]
            if not action_matches:
                if target_clauses and stated_volume == requested_volume:
                    return
                continue
            midpoint = (volume_match.start() + volume_match.end()) / 2
            nearest_action = min(
                action_matches,
                key=lambda action: min(
                    abs(midpoint - action[0]), abs(midpoint - action[1])
                ),
            )
            if (
                nearest_action[2] == expected_action
                and stated_volume == requested_volume
            ):
                return

    raise ClarificationRequested(
        question=_clarification_question(name, arguments),
        reason=(
            "The instruction does not explicitly state this volume for "
            "the requested action."
        ),
    )
