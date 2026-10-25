"""End-to-end proof of concept: natural language -> LLM -> handler."""

import json
from openai import OpenAI

from config import config
from prompts import build_messages
from handler import SimulatedHandler, validate_step, InvalidStepError


def query_llm(user_input: str) -> str:
    """Send the user input to the LLM and return the raw response text."""
    client = OpenAI(api_key=config.API_KEY, base_url=config.BASE_URL)
    response = client.chat.completions.create(
        model=config.MODEL,
        messages=build_messages(user_input),
        temperature=config.TEMPERATURE,
        max_tokens=config.MAX_TOKENS,
    )
    return response.choices[0].message.content.strip()


def parse_and_validate(raw: str):
    """Parse the LLM response and validate each step."""
    # Clean up common LLM artifacts (code fences, leading/trailing text)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON:\n{raw}") from e

    if "steps" not in data or not isinstance(data["steps"], list):
        raise ValueError(f"Missing or invalid 'steps' field: {data}")

    return [validate_step(step) for step in data["steps"]]


def run(user_input: str) -> None:
    print(f"[INPUT] {user_input}")
    raw = query_llm(user_input)
    print(f"[LLM RAW] {raw}")

    try:
        steps = parse_and_validate(raw)
    except (ValueError, InvalidStepError) as e:
        print(f"[ERROR] {e}")
        return

    handler = SimulatedHandler()
    handler.execute(steps)


if __name__ == "__main__":
    example = "Transfer 100 µL from A1 to B1, then 50 µL from B2 to C3."
    run(example)