"""Shared model selection helpers.

Use `LLM_TEXT_MODEL` as the single switch for text LLM model selection.
`VOLCENGINE_TEXT_MODEL` is kept as a backward-compatible fallback.
"""
import os
from dotenv import load_dotenv

load_dotenv()

TEXT_MODEL_ENV_KEY = "LLM_TEXT_MODEL"
LEGACY_TEXT_MODEL_ENV_KEY = "VOLCENGINE_TEXT_MODEL"
DEFAULT_TEXT_MODEL = "deepseek-v3-250324"


def _first_non_empty(*values: str) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def get_text_llm_model() -> str:
    """Resolve text model from env with unified priority."""
    resolved = _first_non_empty(
        os.getenv(TEXT_MODEL_ENV_KEY, ""),
        os.getenv(LEGACY_TEXT_MODEL_ENV_KEY, ""),
        DEFAULT_TEXT_MODEL,
    )
    return resolved
