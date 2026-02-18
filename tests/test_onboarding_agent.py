import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app
from app.agents.state import OnboardingState
from app.agents.onboarding import node_search_references, node_generate_roadmap

client = TestClient(app)

@pytest.fixture
def mock_search_tool():
    with patch("app.agents.onboarding.search_scholar_mock") as mock:
        mock.return_value = [
            {"title": "Test Paper", "url": "http://test.com", "authors": ["Me"], "year": 2024}
        ]
        yield mock

def test_node_search_references(mock_search_tool):
    state = {"topic": "AI in Medicine", "messages": []}
    result = node_search_references(state)
    
    assert result["current_step"] == "select_articles"
    assert len(result["suggested_articles"]) == 1
    assert result["suggested_articles"][0]["title"] == "Test Paper"

def test_node_generate_roadmap():
    state = {"deadline": "2 months"}
    result = node_generate_roadmap(state)
    
    assert result["current_step"] == "confirm"
    assert len(result["roadmap"]) > 0
    assert "Literature Review" in [t["title"] for t in result["roadmap"]]

@patch("app.agents.onboarding.onboarding_graph.ainvoke")
def test_chat_onboarding_endpoint(mock_invoke):
    # Mock Graph Response
    mock_invoke.return_value = {
        "messages": [MagicMock(content="Hello, how can I help?")],
        "suggested_articles": [],
        "roadmap": []
    }
    
    response = client.post(
        "/api/v1/onboarding/chat",
        json={"message": "I want to research coffee", "conversation_id": "123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Hello, how can I help?"
