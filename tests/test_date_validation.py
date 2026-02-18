import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import json
from langchain_core.messages import AIMessage, HumanMessage

# Mock the state
from app.agents.state import OnboardingState

# Import the function to test
# We need to patch 'get_llm' or the 'llm' object inside onboarding.py
# Since 'llm' is global in onboarding.py, we can patch it there.


def test_date_validation_logic():
    # Setup
    today = datetime.now()
    valid_date = (today + timedelta(days=40)).strftime("%Y-%m-%d")
    short_date = (today + timedelta(days=10)).strftime("%Y-%m-%d")
    past_date = (today - timedelta(days=10)).strftime("%Y-%m-%d")

    # Mock LLM response for valid date
    with patch("app.agents.onboarding.llm") as mock_llm:
        # Case 1: Valid Date
        mock_llm.invoke.return_value = AIMessage(
            content=json.dumps({"date": valid_date})
        )

        from app.agents.onboarding import node_process_deadline

        state = {
            "messages": [
                AIMessage(content="Qual o prazo?"),
                HumanMessage(content=f"O prazo é {valid_date}"),
            ]
        }

        result = node_process_deadline(state)
        assert result.get("deadline") == valid_date
        assert result.get("current_step") == "generate_roadmap"

        # Case 2: Past Date
        mock_llm.invoke.return_value = AIMessage(
            content=json.dumps({"date": past_date})
        )
        state["messages"] = [
            AIMessage(content="Qual o prazo?"),
            HumanMessage(content="Ontem"),
        ]

        result = node_process_deadline(state)
        assert "escolha uma data futura" in result["messages"][0].content
        assert result.get("current_step") == "wait_deadline"

        # Case 3: Too Soon (< 30 days)
        mock_llm.invoke.return_value = AIMessage(
            content=json.dumps({"date": short_date})
        )
        state["messages"] = [
            AIMessage(content="Qual o prazo?"),
            HumanMessage(content="Daqui a 10 dias"),
        ]

        result = node_process_deadline(state)
        assert "prazo é muito curto" in result["messages"][0].content
        assert result.get("current_step") == "wait_deadline"

        # Case 4: No Date Extracted
        mock_llm.invoke.return_value = AIMessage(content=json.dumps({"date": None}))
        state["messages"] = [
            AIMessage(content="Qual o prazo?"),
            HumanMessage(content="Não sei"),
        ]

        result = node_process_deadline(state)
        assert "Não entendi a data" in result["messages"][0].content
        assert result.get("current_step") == "wait_deadline"


if __name__ == "__main__":
    # Manually run test if pytest not available or for quick check
    try:
        test_date_validation_logic()
        print("All date validation tests PASSED!")
    except AssertionError as e:
        print(f"Test FAILED: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
