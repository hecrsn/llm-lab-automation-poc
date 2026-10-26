"""Tool definitions for OpenAI-compatible function calling."""

TRANSFER_LIQUID_TOOL = {
    "type": "function",
    "function": {
        "name": "transfer_liquid",
        "description": (
            "Transfer a volume of liquid from a source well to a destination well "
            "on a 96-well plate. Use this for every single transfer step."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Source well position, e.g. 'A1'.",
                },
                "destination": {
                    "type": "string",
                    "description": "Destination well position, e.g. 'B1'.",
                },
                "volume_ul": {
                    "type": "number",
                    "description": "Volume to transfer in microliters.",
                },
            },
            "required": ["source", "destination", "volume_ul"],
        },
    },
}

TOOLS = [TRANSFER_LIQUID_TOOL]

REQUEST_CLARIFICATION_TOOL = {
    "type": "function",
    "function": {
        "name": "request_clarification",
        "description": (
            "Ask the user for clarification when the instruction is ambiguous, "
            "incomplete, or cannot be safely translated into a liquid transfer. "
            "Use this instead of guessing. Never fabricate missing values."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The specific question to ask the user.",
                },
                "reason": {
                    "type": "string",
                    "description": "Why the instruction is unclear (missing volume, ambiguous position, contradictory steps, etc.).",
                },
            },
            "required": ["question", "reason"],
        },
    },
}

TOOLS = [TRANSFER_LIQUID_TOOL, REQUEST_CLARIFICATION_TOOL]