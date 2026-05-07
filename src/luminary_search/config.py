"""Model and environment configuration for luminary_search.

API keys are loaded from a .env file in the project root automatically.
To set up, copy .env.example to .env and fill in your keys.

This is also the single place to change the model used across the entire
pipeline. Every component reads from DEFAULT_MODEL.

To switch models, change DEFAULT_MODEL below and restart.

Supported model strings (LangChain init_chat_model format):
    "openai:gpt-4.1"                        <- default
    "openai:gpt-4o"
    "openai:gpt-4.1-mini"
    "anthropic:claude-sonnet-4-20250514"
    "anthropic:claude-opus-4-20250514"
    "google_genai:gemini-2.0-flash"

Author: Deepthi R
"""

from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

# Load .env from the project root (two levels up from this file:
# src/luminary_search/config.py -> src/luminary_search -> src -> project root)
_env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

# ---------------------------------------------------------------
# Change this one line to switch the model for the whole pipeline
# ---------------------------------------------------------------
DEFAULT_MODEL = "openai:gpt-4.1"
# ---------------------------------------------------------------


def get_model(**kwargs):
    """Return a chat model instance using DEFAULT_MODEL.

    Any extra kwargs (e.g. temperature=0.0, max_tokens=32000) are forwarded
    to the underlying model constructor.
    """
    return init_chat_model(model=DEFAULT_MODEL, **kwargs)
