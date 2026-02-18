from typing import Optional
from app.core.config import settings


def get_llm():
    """
    Returns the configured LLM instance.
    Supports both Ollama and Google GenAI (Gemini) based on configuration.
    """
    if settings.GEMINI_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.3,
                max_retries=5,
                convert_system_message_to_human=True,  # Sometimes needed for older models, but harmless
            )
        except ImportError:
            print("WARNING: langchain_google_genai not installed. Fallback to Ollama?")
            raise

    # Fallback to Ollama if no API key
    from langchain_ollama import ChatOllama

    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL, temperature=0.3
    )
