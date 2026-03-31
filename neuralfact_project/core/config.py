import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_PRICE_1M_INPUT_TOKENS = 0.5
GEMINI_PRICE_1M_OUTPUT_TOKENS = 3

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
DEEPSEEK_PRICE_1M_INPUT_TOKENS = 0.28
DEEPSEEK_PRICE_1M_OUTPUT_TOKENS = 0.42

# Export default prices (for backwards compatibility)
PRICE_1M_INPUT_TOKENS = DEEPSEEK_PRICE_1M_INPUT_TOKENS
PRICE_1M_OUTPUT_TOKENS = DEEPSEEK_PRICE_1M_OUTPUT_TOKENS

def get_deepseek_llm():
    """Khởi tạo mô hình DeepSeek"""
    request_timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "12"))
    temperature = float(os.getenv("LLM_TEMPERATURE", "0"))

    return ChatOpenAI(
        base_url="https://api.deepseek.com/v1",
        api_key=DEEPSEEK_API_KEY,
        model="deepseek-chat",
        request_timeout=request_timeout,
        temperature=temperature
    )

def get_gemini_llm():
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