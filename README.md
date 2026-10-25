# LLM-to-Liquid-Handler Proof of Concept

A minimal proof of concept that translates natural language experiment
descriptions into structured liquid-handling commands using a large
language model (LLM).

## What it does

1. Takes a natural language instruction like:
   "Transfer 100 µL from A1 to B1, then 50 µL from B2 to C3"
2. Sends it to an LLM with few-shot examples
3. Parses and validates the JSON output
4. Passes the structured steps to a simulated liquid handler

## Why

This project explores how LLMs can be connected to laboratory equipment
through software interfaces - a core idea behind AI-driven laboratory
automation in pharmaceutical research.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt