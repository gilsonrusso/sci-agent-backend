import asyncio
import json
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        payload = {
            "message": "ola gostaria de falar sobre machine learning na area da educacao",
            "conversation_id": "test-cli-uuid5",
            "project_context": {}
        }
        async with client.stream("POST", "http://localhost:8000/api/v1/onboarding/chat/stream", json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    print(line)

asyncio.run(main())
