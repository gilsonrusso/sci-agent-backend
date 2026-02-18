import time
from app.core.llm import get_llm
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.onboarding import SYSTEM_PROMPT


def test_llm():
    print("Initializing LLM...")
    llm = get_llm()
    print(f"LLM Initialized: {type(llm)}")

    print("Invoking with FULL SYSTEM PROMPT and User Query...")
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content="Como criar um site em React?"),
    ]

    start = time.time()
    try:
        response = llm.invoke(messages)
        end = time.time()
        print(f"Response ({end-start:.2f}s): {response.content[:200]}...")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_llm()
