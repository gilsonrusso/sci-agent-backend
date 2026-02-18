import httpx
import asyncio


async def verify_persona():
    url = "http://localhost:8000/api/v1/onboarding/chat"

    # Turn 0: Guardrail Test
    payload = {
        "message": "Como criar um site em React?",
        "conversation_id": "test-persona-002",
    }
    print(f"\n--- Persona Test (Non-Academic Query) ---")
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(url, json=payload, timeout=60.0)
            print(f"Status: {r.status_code}")
            if r.status_code == 200:
                print(f"Response: {r.json()['message']}")
            else:
                print(f"Error: {r.text}")
        except Exception as e:
            print(f"Exception: {e}")


if __name__ == "__main__":
    asyncio.run(verify_persona())
