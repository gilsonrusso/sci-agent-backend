from typing import Any, Dict, List
from langchain_core.messages import BaseMessage


class MessageParser:
    """
    Isolates the responsibility of parsing raw `BaseMessage` arrays from LangChain
    into clean human-readable dictionaries containing text and the acting agent's name.
    """

    AGENT_NAME_MAPPING = {
        "supervisor_agent": "Supervisor",
        "idea_refiner_subagent": "Guia de Exploração",
        "idea_refiner_agent": "Guia de Exploração",
        "search_specialist_subagent": "Especialista de Busca",
        "search_specialist": "Especialista de Busca",
        "curation_manager": "Gerente de Curadoria",
        "write_todos": "Supervisor",
    }

    @classmethod
    def parse_turn(cls, messages: List[BaseMessage], node_name: str = None) -> Dict[str, Any]:
        """
        Extracts combined text from the last AI turn (messages after the last Human message).
        """
        if not messages:
            return {"text": "", "agent_name": "Supervisor"}

        # Use only messages from the current turn
        current_turn_msgs = []
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "human":
                break
            current_turn_msgs.append(msg)
        current_turn_msgs.reverse()

        # Look for messages from the current turn (AI and Tool results)
        allowed_types = ("ai", "tool")
        turn_messages = [
            m for m in current_turn_msgs if hasattr(m, "type") and m.type in allowed_types
        ]

        # Initial guess from node_name
        last_friendly_name = cls.AGENT_NAME_MAPPING.get(node_name, node_name or "Supervisor")

        # Refine 'task' node name by looking for subagent_type in tool_calls
        if node_name == "task":
            for msg in reversed(messages):
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        if tc.get("name") == "task":
                            subagent_type = tc.get("args", {}).get("subagent_type")
                            if subagent_type:
                                last_friendly_name = cls.AGENT_NAME_MAPPING.get(subagent_type, subagent_type)
                                break
                    if last_friendly_name != "task": break

        # Map technical tool nodes to Supervisor
        if node_name == "write_todos":
            last_friendly_name = "Supervisor"

        full_text = []

        for msg in turn_messages:
            content = msg.content
            
            # Skip technical tool messages (JSON or empty or internal status)
            if msg.type == "tool":
                # Check for technical status updates
                technical_prefixes = ["Updated todo list", "Successfully"]
                if any(str(content).startswith(p) for p in technical_prefixes):
                    continue

                try:
                    # If it's valid JSON, it's probably technical data (like search results)
                    import json
                    json.loads(str(content))
                    continue
                except:
                    # Not JSON, might be a subagent response text
                    pass

            if isinstance(content, list):
                text_parts = [
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                text_val = "".join(text_parts).strip()
            else:
                text_val = str(content).strip()

            if text_val:
                full_text.append(text_val)

            # Try to identify a more specific agent name from the message itself
            r_name = getattr(msg, "name", "system") or "system"
            if r_name != "system":
                last_friendly_name = cls.AGENT_NAME_MAPPING.get(r_name, r_name)

        return {
            "text": "\n\n".join(full_text).strip(),
            "agent_name": last_friendly_name,
        }
