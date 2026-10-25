"""Configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
    API_KEY: str = os.getenv("LLM_API_KEY", "ollama")
    MODEL: str = os.getenv("LLM_MODEL", "llama3.1")
    BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    TEMPERATURE: float = 0.0  # deterministic output for structured tasks
    MAX_TOKENS: int = 500


config = Config()