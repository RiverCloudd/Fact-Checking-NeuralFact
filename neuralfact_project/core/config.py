import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
PRICE_1M_INPUT_TOKENS = 0.28
PRICE_1M_OUTPUT_TOKENS = 0.42

def get_llm():
    """Khởi tạo mô hình DeepSeek"""
    request_timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "12"))
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "350"))
    temperature = float(os.getenv("LLM_TEMPERATURE", "0"))

    return ChatOpenAI(
        base_url="https://api.deepseek.com/v1",
        api_key=DEEPSEEK_API_KEY,
        model="deepseek-chat",
        request_timeout=request_timeout,
        max_tokens=max_tokens,
        temperature=temperature
    )
