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

MAX_TURNS = 10  # safety limit against infinite tool-call loops

SYSTEM_PROMPT = (
    "You are a laboratory automation assistant. "
    "Use the transfer_liquid tool to perform transfers. "
    "If the user instruction is ambiguous, incomplete, or contains values "
    "you cannot infer safely (e.g. missing volume, unclear well position, "
    "contradictory steps), call request_clarification instead of guessing. "
    "Never fabricate positions or volumes."
)
from handler import SimulatedHandler, execute_tool_call, ClarificationRequested

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
            print(f"[HANDLER] Run complete: {len(handler.executed)} steps executed")
            return

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as e:
                print(f"[ERROR] Invalid tool arguments: {e}")
                return

            print(f"[LLM TOOL CALL] {name}({arguments})")

            try:
                result = execute_tool_call(name, arguments, handler)
            except ClarificationRequested as c:
                print(f"[CLARIFICATION NEEDED] {c.question}")
                print(f"[REASON] {c.reason}")
                print(f"[HANDLER] Run aborted: {len(handler.executed)} steps executed before clarification request.")
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

    
def run(user_input: str) -> None:
    print(f"[INPUT] {user_input}")

    client = OpenAI(api_key=config.API_KEY, base_url=config.BASE_URL)
    handler = SimulatedHandler()

    messages = [{"role": "user", "content": user_input}]

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
            print(f"[HANDLER] Run complete: {len(handler.executed)} steps executed")
            return

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as e:
                print(f"[ERROR] Invalid tool arguments: {e}")
                return

            print(f"[LLM TOOL CALL] {name}({arguments})")
            result = execute_tool_call(name, arguments, handler)
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
    example = "Wells A1 bis C12 werden mit Agonist A befüllt, D1 bis F12 mit Agonist B. Sauge davor 200 µl aus allen Wells ab"
    run(example)