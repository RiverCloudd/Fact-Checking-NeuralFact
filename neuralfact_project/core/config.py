import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
PRICE_1M_INPUT_TOKENS = 0.5
PRICE_1M_OUTPUT_TOKENS = 3

def get_llm():
    """Khoi tao mo hinh Gemini."""
    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "12"))
    temperature = float(os.getenv("LLM_TEMPERATURE", "0"))
    model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

    if not GEMINI_API_KEY:
        raise ValueError("Missing GEMINI_API_KEY or GOOGLE_API_KEY in environment")

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=GEMINI_API_KEY,
        timeout=timeout,
        temperature=temperature
    )
