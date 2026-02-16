from langchain_ollama import ChatOllama
from app.core.config import settings
import asyncio


async def test_ollama():
    print(
        f"Connecting to Ollama at {settings.OLLAMA_BASE_URL} with model {settings.OLLAMA_MODEL}..."
    )
    try:
        llm = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=0.7,
        )
        response = llm.invoke("Hello, are you working?")
        print("Response received:")
        print(response.content)
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")


if __name__ == "__main__":
    asyncio.run(test_ollama())
