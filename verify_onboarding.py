import httpx
import asyncio
import sys


async def test_chat():
    url = "http://localhost:8000/api/v1/onboarding/chat"
    payload = {
        "message": "Quero pesquisar sobre Machine Learning e Medicina",
        "conversation_id": "test-123",
    }

    print(f"Sending request to {url}...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=120.0)

        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Response:", response.json())
        else:
            print("Error Response:", response.text)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_chat())
