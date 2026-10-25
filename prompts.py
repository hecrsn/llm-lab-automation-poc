"""Prompt templates with few-shot examples."""

SYSTEM_PROMPT = """You are a laboratory automation assistant. Your task is
to translate natural language descriptions of liquid handling experiments
into a structured JSON format.

The JSON must follow this schema:
{
  "steps": [
    {"source": "A1", "destination": "B1", "volume_ul": 100}
  ]
}

Rules:
- Positions are in the format [A-Z][1-9][0-9]? (e.g. A1, B12).
- volume_ul must be a positive integer or float.
- Output ONLY valid JSON. Do not add explanations, markdown or code fences.
"""

FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": "Transfer 200 µL from A1 to B1.",
    },
    {
        "role": "assistant",
        "content": '{"steps": [{"source": "A1", "destination": "B1", "volume_ul": 200}]}',
    },
    {
        "role": "user",
        "content": "Move 50 µL from C2 to D4, then 75 µL from E1 to F1.",
    },
    {
        "role": "assistant",
        "content": (
            '{"steps": ['
            '{"source": "C2", "destination": "D4", "volume_ul": 50},'
            '{"source": "E1", "destination": "F1", "volume_ul": 75}'
            ']}'
        ),
    },
]


def build_messages(user_input: str) -> list[dict]:
    """Build the full message list for the LLM call."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(FEW_SHOT_EXAMPLES)
    messages.append({"role": "user", "content": user_input})
    return messages