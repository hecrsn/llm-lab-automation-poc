"""Plan-first function-calling entry point for liquid-handling instructions."""

import json

from openai import OpenAI

from config import config
from handler import ClarificationRequested, SimulatedHandler, execute_tool_call
from instruction_validation import (
    validate_tool_call_location,
    validate_tool_call_volume,
)
from tools import TOOLS

MAX_TURNS = 15

PLAN_SYSTEM_PROMPT = (
    "You are a laboratory automation planning assistant.\n"
    "Analyse the user's instruction and write a numbered plan of every step\n"
    "in the ORDER they must be executed. Pay special attention to:\n"
    "- Temporal markers ('davor', 'zuerst', 'before', 'then', 'after').\n"
    "- Scope markers ('alle Wells', 'all wells') - list every affected range.\n"
    "- Explicit ranges (e.g. 'A1 to C12').\n"
    "Output ONLY the numbered plan, one step per line, in the final order.\n"
    "Do not call any tools yet. Do not add explanations."
)

EXECUTE_SYSTEM_PROMPT = (
    "You are a laboratory automation assistant. Execute the plan below\n"
    "using the provided tools, one tool call per plan step, in the exact\n"
    "order given. Do not reorder, skip or add steps.\n"
    "For every reagent fill, use only an explicitly stated source well.\n"
    "If its source well is missing, request clarification before filling.\n"
    "After all steps, summarize only the operations that were executed."
)


def run(user_input: str) -> None:
    print(f"[INPUT] {user_input}")

    client = OpenAI(api_key=config.API_KEY, base_url=config.BASE_URL)
    plan_response = client.chat.completions.create(
        model=config.MODEL,
        messages=[
            {"role": "system", "content": PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        temperature=config.TEMPERATURE,
        max_tokens=config.MAX_TOKENS,
    )
    plan = plan_response.choices[0].message.content
    if not plan:
        print("[ERROR] The model returned an empty plan.")
        return

    print("[PLAN]")
    print(plan)

    handler = SimulatedHandler()
    messages = [
        {"role": "system", "content": EXECUTE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"User instruction:\n{user_input}\n\nPlan:\n{plan}",
        },
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
                except json.JSONDecodeError as error:
                    print(f"[ERROR] Invalid tool arguments: {error}")
                    return

                print(f"[LLM TOOL CALL] {name}({arguments})")
                validate_tool_call_location(user_input, name, arguments)
                validate_tool_call_volume(user_input, name, arguments)
                parsed_tool_calls.append((tool_call, name, arguments))
        except ClarificationRequested as clarification:
            print(f"[CLARIFICATION NEEDED] {clarification.question}")
            print(f"[REASON] {clarification.reason}")
            print(
                "[HANDLER] Run aborted: "
                f"{len(handler.operations)} operations logged before clarification request."
            )
            return

        for tool_call, name, arguments in parsed_tool_calls:
            try:
                result = execute_tool_call(name, arguments, handler)
            except ClarificationRequested as clarification:
                print(f"[CLARIFICATION NEEDED] {clarification.question}")
                print(f"[REASON] {clarification.reason}")
                print(
                    "[HANDLER] Run aborted: "
                    f"{len(handler.operations)} operations logged before clarification request."
                )
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
        "Wells A1 bis C12 werden mit Agonist A befüllt, "
        "D1 bis F12 mit Agonist B. "
        "Sauge davor 200 µl aus allen Wells ab."
    )
    run(example)
