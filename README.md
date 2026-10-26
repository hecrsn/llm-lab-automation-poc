# LLM-to-Liquid-Handler Proof of Concept

A proof of concept that explores how large language models (LLMs) can be
connected to laboratory equipment through software interfaces - a core
idea behind AI-driven laboratory automation in pharmaceutical research.

The project implements two approaches and documents where each of them
succeeds and fails.

## What it does

The PoC translates natural language experiment descriptions into
executable liquid-handling commands, using a simulated liquid handler as
a stand-in for real hardware.

Two approaches are implemented:

1. **JSON mode** (`main.py`): The LLM is asked to return a structured
   JSON object describing the transfer steps. The output is parsed,
   validated and passed to the handler.

2. **Function calling** (`main_function_calling.py`): The LLM receives
   a set of tool definitions and decides itself which tool to call.
   The script executes the call, feeds the result back to the model,
   and receives a final natural-language summary. A clarification tool
   allows the model to ask the user instead of guessing.

## Why

This project explores how LLMs can be connected to laboratory equipment
through software interfaces - a core idea behind AI-driven laboratory
automation in pharmaceutical research. It also documents the limitations
observed when using a small local model (`llama3.1:8b`) for this task.

## Project structure

```
llm-lab-automation-poc/
├── config.py                  # Configuration from .env
├── prompts.py                 # System prompt and few-shot examples (JSON mode)
├── tools.py                   # Tool definitions for function calling
├── handler.py                 # Simulated handler + validation + tool execution
├── main.py                    # JSON-mode entry point
├── main_function_calling.py   # Function-calling entry point
├── tests/
│   └── test_handler.py
├── pytest.ini
├── requirements.txt
└── README.md
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure the LLM

The project supports any OpenAI-compatible API (OpenAI, Azure OpenAI,
or a local model via Ollama).

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

For a local model via Ollama (no API key needed, no usage cost):

```
LLM_PROVIDER=ollama
LLM_API_KEY=ollama
LLM_MODEL=llama3.1
LLM_BASE_URL=http://localhost:11434/v1
```

Make sure Ollama is running and the model is available:

```bash
ollama list
ollama pull llama3.1   # if not yet loaded
```

### 3. Run

**JSON mode:**

```bash
python main.py
```

**Function calling:**

```bash
python main_function_calling.py
```

### 4. Run tests

```bash
pytest
```

## Example output (JSON mode)

Input:
```
Transfer 100 µL from A1 to B1, then 50 µL from B2 to C3
```

Output:
```
[INPUT] Transfer 100 µL from A1 to B1, then 50 µL from B2 to C3.
[LLM RAW] {"steps": [{"source": "A1", "destination": "B1", "volume_ul": 100},
                     {"source": "B2", "destination": "C3", "volume_ul": 50}]}
[HANDLER] Aspirate 100 µL from A1
[HANDLER] Dispense 100 µL into B1
[HANDLER] Aspirate 50 µL from B2
[HANDLER] Dispense 50 µL into C3
[HANDLER] Run complete: 2 steps executed
```

## Example output (function calling)

Input:
```
Transfer 100 µL from A1 to B1, then 50 µL from B2 to C3.
```

Output:
```
[INPUT] Transfer 100 µL from A1 to B1, then 50 µL from B2 to C3.
[LLM TOOL CALL] transfer_liquid({'source': 'A1', 'destination': 'B1', 'volume_ul': 100})
[HANDLER] Aspirate 100 µL from A1
[HANDLER] Dispense 100 µL into B1
[TOOL RESULT] Success: transferred 100 µL from A1 to B1.
[LLM TOOL CALL] transfer_liquid({'source': 'B2', 'destination': 'C3', 'volume_ul': 50})
[HANDLER] Aspirate 50 µL from B2
[HANDLER] Dispense 50 µL into C3
[TOOL RESULT] Success: transferred 50 µL from B2 to C3.
[LLM FINAL] I have transferred 100 µL from A1 to B1 and 50 µL from B2 to C3.
[HANDLER] Run complete: 2 steps executed
```

## Findings

All tests were run with `llama3.1:8b` via Ollama at `temperature=0.0`.

### What works well

- **Simple multi-step transfers** ("Transfer 100 µL from A1 to B1, then
  50 µL from B2 to C3"): reliable JSON output and correct tool calls
  across repeated runs.
- **Alternative phrasing** ("Move 25 µL from B2 to C3 and 30 µL from
  D4 to E5"): correctly parsed.
- **Boundary positions** (H12, A1): correctly recognised.
- **Missing volume** ("Transfer some liquid from A1 to B1"): the model
  calls `request_clarification` instead of fabricating a volume - though
  reliability varies (see below).

### Failure case: complex multi-well instruction

Input (German):

```
Wells A1 bis C12 werden mit Agonist A befüllt, D1 bis F12 mit Agonist B.
Sauge davor 200 µl aus allen Wells ab.
```

Observed behaviour:

- The model ignored the range semantics (`A1–C12` = 36 wells).
- It interpreted "Sauge ab" (aspirate) as a transfer operation and
  fabricated a chain of 15 transfers (A1→B1→C1→D1→E1→F1→A2→...).
- It produced no fill operation for Agonist A or B.
- The final answer claimed success ("Die 200 µL aus allen Wells wurden
  abgesaugt"), which is factually incorrect.

Root causes:

1. **Missing tools.** The tool set only defines `transfer_liquid`.
   There is no `aspirate`, `dispense` or `fill_wells` tool, so the model
   forced the instruction into the only tool it had.
2. **No range decomposition.** The model has no mechanism to expand a
   range like `A1–C12` into individual wells.
3. **Confidently wrong output.** The final natural-language summary
   reported success for actions that were not performed.

### Limitations of `llama3.1:8b` for tool use

- Tool calling works for simple, single-intent instructions.
- Complex or multi-intent instructions are frequently misinterpreted.
- The model occasionally ignores tool schemas and asks questions in
  plain text instead of calling `request_clarification`.
- Range instructions and German-language instructions increase the
  failure rate.

## Recommendations

Based on the observed failures, a production-grade system would need:

1. **Dedicated tools** for `aspirate`, `dispense`, `fill_wells` and
   `aspirate_wells`, so the model is not forced to map every intent
   onto `transfer_liquid`.
2. **Explicit range decomposition.** Either provide a `fill_wells(range)`
   tool that accepts a well range, or add a pre-processing step that
   expands ranges into individual wells before the LLM sees them.
3. **A validation layer** that checks whether the number and type of
   tool calls match the intent. For example, an instruction covering 36
   wells should produce at least 36 operations - 15 calls should trigger
   a warning and abort.
4. **A confirmation step** for multi-well or multi-step operations:
   show the planned sequence to the user before execution.
5. **A larger model or a planning layer** for complex instructions.
   `llama3.1:8b` is sufficient for single transfers but not for
   multi-intent laboratory workflows.
6. **A retry loop with corrective prompt** when the model produces
   invalid JSON or ignores tool schemas.

## Possible extensions

- `aspirate` and `fill_wells` tools
- Range decomposition and validation layer
- Retry loop on invalid output
- Support for multiple LLM providers via a unified interface
- Validation of positions against a defined labware layout

## License

MIT