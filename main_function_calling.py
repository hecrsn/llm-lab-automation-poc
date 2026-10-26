"""Function calling version: the LLM decides which tool to call.

Unlike main.py (JSON mode), here the model does not produce JSON as text.
Instead, it returns structured tool_calls that this script executes,
feeds back to the model, and then receives a final natural-language summary.
"""

import json
from openai import OpenAI

from config import config
from tools import TOOLS
from handler import SimulatedHandler, execute_tool_call
from instruction_validation import (
    validate_tool_call_location,
    validate_tool_call_volume,
)

MAX_TURNS = 10  # safety limit against infinite tool-call loops

SYSTEM_PROMPT = (
    "You are a laboratory automation assistant controlling a liquid handler.\n\n"
    "Tool selection rules:\n"
    "- transfer_liquid: move liquid from ONE well to ANOTHER well.\n"
    "- aspirate: remove liquid from a SINGLE well (waste).\n"
    "- dispense: add liquid into a SINGLE well.\n"
    "- fill_wells: fill a rectangular RANGE with a reagent.\n"
    "- aspirate_wells: remove liquid from every well in a RANGE.\n"
    "- request_clarification: ask the user when the instruction is ambiguous.\n\n"
    "Critical rules:\n"
    "- Never map an 'aspirate' or 'absaugen' action to transfer_liquid.\n"
    "- Never map a 'fill' or 'befüllen' action to a chain of transfers.\n"
    "- For ranges like 'A1 to C12', use fill_wells or aspirate_wells with\n"
    "  range_start and range_end. Do NOT enumerate wells yourself.\n"
    "- Do not fabricate positions or volumes. If a value is missing, call\n"
    "  request_clarification.\n"
    "- For every reagent fill, require the reagent's source well location.\n"
    "  If it is not explicitly given, request clarification before filling.\n"
    "- Temporal order: words such as 'davor', 'zuerst', 'first', and 'before'\n"
    "  mean those steps must be executed before the other steps, even when\n"
    "  they appear later in the sentence. Words such as 'danach', 'then',\n"
    "  and 'after' mean those steps come afterward.\n"
    "- Execute tool calls in the correct temporal order. Never execute an\n"
    "  aspiration after a fill when the instruction says 'davor' (before).\n"
    "- When 'alle Wells' or 'all wells' follows multiple named ranges, it\n"
    "  refers to all previously mentioned ranges; cover every such range.\n"
    "- Verify that every mentioned range is covered before producing the\n"
    "  final summary.\n"
    "- After executing all steps, summarize only the operations that were\n"
    "  actually performed. Do not claim actions that were not executed."
)

from handler import ClarificationRequested

def run(user_input: str) -> None:
    print(f"[INPUT] {user_input}")

    client = OpenAI(api_key=config.API_KEY, base_url=config.BASE_URL)
    handler = SimulatedHandler()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]

    for turn in range(MAX_TURNS):
        response = client.chat.completions.create(
            model=config.MODEL,
            messages=messages,
            tools=TOOLS,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
        )

        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            print(f"[LLM FINAL] {message.content}")
            print(f"[HANDLER] Run complete: {len(handler.operations)} operations logged")
            return

        parsed_tool_calls = []
        try:
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Invalid tool arguments: {e}")
                    return

                print(f"[LLM TOOL CALL] {name}({arguments})")
                validate_tool_call_location(user_input, name, arguments)
                validate_tool_call_volume(user_input, name, arguments)
                parsed_tool_calls.append((tool_call, name, arguments))
        except ClarificationRequested as c:
            print(f"[CLARIFICATION NEEDED] {c.question}")
            print(f"[REASON] {c.reason}")
            print(f"[HANDLER] Run aborted: {len(handler.operations)} operations logged before clarification request.")
            return

        for tool_call, name, arguments in parsed_tool_calls:
            try:
                result = execute_tool_call(name, arguments, handler)
            except ClarificationRequested as c:
                print(f"[CLARIFICATION NEEDED] {c.question}")
                print(f"[REASON] {c.reason}")
                print(f"[HANDLER] Run aborted: {len(handler.operations)} operations logged before clarification request.")
                return

            print(f"[TOOL RESULT] {result}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    print(f"[ERROR] Max turns ({MAX_TURNS}) reached without final answer.")

if __name__ == "__main__":
    example = (
        "Wells A1 bis C12 werden mit 50 µl Agonist A (H11)befüllt, "
        "D1 bis F12 mit 40 µl Agonist B (H12). "
        "Sauge davor 200 µl aus allen Wells ab."
    )
    run(example)