import httpx
import asyncio
import sys
from datetime import datetime, timedelta


async def test_memory():
    url = "http://localhost:8000/api/v1/onboarding/chat"
    conv_id = "test-memory-001"

    # Turn 0: Guardrail Test
    payload0 = {
        "message": "Como criar um site em React?",
        "conversation_id": "test-guardrail-001",
    }
    print(f"\n--- Turn 0 (Guardrail Test) ---")
    async with httpx.AsyncClient() as client:
        try:
            r0 = await client.post(url, json=payload0, timeout=180.0)
            print(f"Status: {r0.status_code}")
            print(f"Response: {r0.json()['message'][:200]}...")
        except Exception as e:
            print(f"Turn 0 Failed: {e}")

    # Turn 1: General Question (Should NOT advance)
    payload1 = {
        "message": "O que é um artigo científico e quais as etapas?",
        "conversation_id": conv_id,
    }
    print(f"\n--- Turn 1 (General Question - Should NOT advance) ---")
    async with httpx.AsyncClient() as client:
        r1 = await client.post(url, json=payload1, timeout=180.0)
        print(f"Status: {r1.status_code}")
        print(f"Response: {r1.json()['message'][:100]}...")
        # Verify step is still 'clarify' (implicit, if it asks for topic)

    # Turn 2: Specific Topic (Should advance)
    payload2 = {
        "message": "Quero pesquisar sobre Machine Learning e Medicina",
        "conversation_id": conv_id,
    }
    print(f"\n--- Turn 2 (Specific Topic - Should Advance) ---")
    async with httpx.AsyncClient() as client:
        r2 = await client.post(url, json=payload2, timeout=180.0)
        print(f"Status: {r2.status_code}")
        print(f"Response: {r2.json()['message'][:100]}...")

    # Turn 3: Select Articles
    payload3 = {
        "message": "Eu selecionei 2 artigos.",  # Message content triggers the "first time asking" check
        "conversation_id": conv_id,
        "project_context": {
            "selected_articles": [
                {"title": "Paper 1", "url": "http://example.com/1", "year": 2024},
                {"title": "Paper 2", "url": "http://example.com/2", "year": 2023},
            ]
        },
    }
    print(f"\n--- Turn 3 (Select Articles, Expect Ask Deadline) ---")
    async with httpx.AsyncClient() as client:
        r3 = await client.post(url, json=payload3, timeout=180.0)
        print(f"Status: {r3.status_code}")
        if r3.status_code != 200:
            print(f"Error Response: {r3.text}")
        else:
            print(f"Response: {r3.json()['message'][:100]}...")

    # Turn 4: Provide Deadline
    # Using a valid future date
    deadline_date = (datetime.now() + timedelta(days=60)).strftime("%d/%m/%Y")
    payload4 = {
        "message": f"A data final é {deadline_date}",
        "conversation_id": conv_id,
    }
    print(f"\n--- Turn 4 (Provide Deadline) ---")
    async with httpx.AsyncClient() as client:
        r4 = await client.post(url, json=payload4, timeout=180.0)
        print(f"Status: {r4.status_code}")
        print(f"Response: {r4.json()['message'][:100]}...")

        if r4.json().get("structured_data", {}).get("roadmap"):
            print("SUCCESS: Roadmap generated!")
            roadmap_data = r4.json()["structured_data"]
            print(f"Title: {roadmap_data.get('project_title')}")
        else:
            print("FAIL: Roadmap not found.")


if __name__ == "__main__":
    asyncio.run(test_memory())
