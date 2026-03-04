import asyncio
import httpx
import traceback


async def main():
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "conversation_id": "test-123",
                "message": "hello",
                "project_context": {},
            }
            async with client.stream(
                "POST",
                "http://localhost:8000/api/v1/onboarding/chat/stream",
                json=payload,
                timeout=30.0,
            ) as response:
                print("Status:", response.status_code)
                async for line in response.aiter_lines():
                    print("Line:", line)
    except Exception as e:
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
