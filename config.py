#TO BE USED IN ALL FILES INSTEAD OF MULTIPLE LLM INITIALIZATIONS ALL OVER THE FILES
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

# Mistral section----mostly used
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large")
MISTRAL_API_URL = os.getenv(
    "MISTRAL_API_URL",
    "https://api.mistral.ai/v1/chat/completions",
)

#for testing or running a local model or openai compatible provider (ex omniroute-openrouter)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "")


def get_llm_client():
    """Return a LangChain chat model client.

    Preference order:
      1. Local / OpenAI-compatible server (LLM_BASE_URL set)
      2. Mistral API (MISTRAL_API_KEY set)

    Raises RuntimeError if neither is configured.
    """
    if LLM_BASE_URL and LLM_API_KEY and LLM_MODEL_NAME:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            max_retries=5,
        )

    if MISTRAL_API_KEY:
        try:
            from langchain_mistralai import ChatMistralAI
        except ImportError:
            raise RuntimeError(
                "langchain-mistralai is not installed. "
                "Install it with: pip install langchain-mistralai"
            )
        return ChatMistralAI(
            api_key=MISTRAL_API_KEY,
            model=MISTRAL_MODEL,
            random_seed=42,
            max_retries=5,
        )

    raise RuntimeError(
        "No LLM configured. Set LLM_BASE_URL/LLM_API_KEY/LLM_MODEL_NAME "
        "for a local server, or MISTRAL_API_KEY for the Mistral API."
    )
