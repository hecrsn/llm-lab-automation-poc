"""Tool definitions for OpenAI-compatible function calling."""

TRANSFER_LIQUID_TOOL = {
    "type": "function",
    "function": {
        "name": "transfer_liquid",
        "description": (
            "Transfer a volume of liquid from a source well to a destination well. "
            "Use ONLY for direct transfers between two wells. "
            "Do NOT use for filling ranges or aspirating to waste."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source well position, e.g. 'A1'."},
                "destination": {"type": "string", "description": "Destination well position, e.g. 'B1'."},
                "volume_ul": {"type": "number", "description": "Volume to transfer in microliters."},
            },
            "required": ["source", "destination", "volume_ul"],
        },
    },
}

ASPIRATE_TOOL = {
    "type": "function",
    "function": {
        "name": "aspirate",
        "description": (
            "Aspirate (remove) a volume of liquid from a single well WITHOUT dispensing it. "
            "Use for waste removal from one well."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Well position, e.g. 'A1'."},
                "volume_ul": {"type": "number", "description": "Volume in microliters."},
            },
            "required": ["source", "volume_ul"],
        },
    },
}

DISPENSE_TOOL = {
    "type": "function",
    "function": {
        "name": "dispense",
        "description": (
            "Dispense a volume of liquid into a single well WITHOUT aspirating from elsewhere. "
            "Use for filling a single well with reagent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {"type": "string", "description": "Well position, e.g. 'A1'."},
                "source_location": {
                    "type": "string",
                    "description": "Source well containing the reagent, e.g. 'H1'.",
                },
                "volume_ul": {"type": "number", "description": "Volume in microliters."},
                "reagent": {"type": "string", "description": "Reagent name, e.g. 'Agonist A'."},
            },
            "required": ["destination", "source_location", "volume_ul", "reagent"],
        },
    },
}

FILL_WELLS_TOOL = {
    "type": "function",
    "function": {
        "name": "fill_wells",
        "description": (
            "Fill a rectangular RANGE of wells with a reagent. Specify the range by "
            "start (top-left) and end (bottom-right). Example: range_start='A1', "
            "range_end='C12' fills 36 wells. The handler expands the range "
            "automatically - do NOT enumerate wells yourself."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "range_start": {"type": "string", "description": "Top-left well, e.g. 'A1'."},
                "range_end": {"type": "string", "description": "Bottom-right well, e.g. 'C12'."},
                "source_location": {
                    "type": "string",
                    "description": "Source well containing the reagent, e.g. 'H1'.",
                },
                "volume_ul": {"type": "number", "description": "Volume per well in microliters."},
                "reagent": {"type": "string", "description": "Reagent name, e.g. 'Agonist A'."},
            },
            "required": [
                "range_start",
                "range_end",
                "source_location",
                "volume_ul",
                "reagent",
            ],
        },
    },
}

ASPIRATE_WELLS_TOOL = {
    "type": "function",
    "function": {
        "name": "aspirate_wells",
        "description": (
            "Aspirate (remove) a volume from every well in a rectangular RANGE. "
            "Use for waste removal across multiple wells. The handler expands "
            "the range automatically - do NOT enumerate wells yourself."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "range_start": {"type": "string", "description": "Top-left well, e.g. 'A1'."},
                "range_end": {"type": "string", "description": "Bottom-right well, e.g. 'C12'."},
                "volume_ul": {"type": "number", "description": "Volume per well in microliters."},
            },
            "required": ["range_start", "range_end", "volume_ul"],
        },
    },
}

REQUEST_CLARIFICATION_TOOL = {
    "type": "function",
    "function": {
        "name": "request_clarification",
        "description": (
            "Ask the user for clarification when the instruction is ambiguous, "
            "incomplete, or cannot be safely translated into liquid handling. "
            "Use this instead of guessing. Never fabricate missing values."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The specific question to ask."},
                "reason": {"type": "string", "description": "Why the instruction is unclear."},
            },
            "required": ["question", "reason"],
        },
    },
}

TOOLS = [
    TRANSFER_LIQUID_TOOL,
    ASPIRATE_TOOL,
    DISPENSE_TOOL,
    FILL_WELLS_TOOL,
    ASPIRATE_WELLS_TOOL,
    REQUEST_CLARIFICATION_TOOL,
]