import pytest
from langchain_core.messages import AIMessage, HumanMessage
from app.infrastructure.ai.streaming.message_parser import MessageParser
from app.infrastructure.ai.streaming.events import TokenEvent, StateUpdateEvent


def test_message_parser_extracts_last_turn():
    messages = [
        HumanMessage(content="Olá"),
        AIMessage(content="Olá! Como posso ajudar?", name="supervisor_agent"),
        HumanMessage(content="Quero pesquisar sobre IA"),
        AIMessage(content="Certo, vou pesquisar.", name="search_specialist_subagent"),
    ]
    
    parsed = MessageParser.parse_turn(messages)
    assert parsed["text"] == "Certo, vou pesquisar."
    assert parsed["agent_name"] == "Especialista de Busca"


def test_message_parser_handles_empty():
    assert MessageParser.parse_turn([]) == {"text": "", "agent_name": "Supervisor"}


def test_token_event_serialization():
    event = TokenEvent(content="Hello")
    chunk = event.to_stream_chunk()
    assert '"type":"token"' in chunk
    assert '"content":"Hello"' in chunk
    assert chunk.endswith("\n")


from app.infrastructure.ai.streaming.state_extractor import StateExtractor


def test_state_extractor_from_state():
    state = {
        "project_title": "AI Research",
        "suggested_articles": ["Art1", "Art2"],
        "random_field": "ignore"
    }
    extracted = StateExtractor.extract_from_state(state)
    assert extracted["project_title"] == "AI Research"
    assert "suggested_articles" in extracted
    assert "random_field" not in extracted


def test_state_extractor_from_interrupt():
    interrupt_payload = {
        "action_requests": [{
            "name": "create_project_and_roadmap",
            "args": {
                "title": "My Project",
                "tasks": [{"title": "Task 1"}]
            }
        }]
    }
    extracted = StateExtractor.extract_from_interrupt(interrupt_payload)
    assert extracted["project_title"] == "My Project"
    assert len(extracted["roadmap"]) == 1

