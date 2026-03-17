from typing import Dict, Any, Optional, List
import json
from langchain_core.messages import HumanMessage, BaseMessage
from app.agents.sub_agents.supervisor import get_onboarding_supervisor
from app.core.observability import get_langfuse_handler
from app.infrastructure.ai.checkpointer import get_checkpointer


class OnboardingService:
    """
    Infrastructure service that encapsulates the LangGraph-based AI Onboarding.
    """

    def __init__(self):
        self.langfuse_handler = get_langfuse_handler()

    AGENT_NAME_MAPPING = {
        "supervisor_agent": "Supervisor",
        "idea_refiner_subagent": "Guia de Exploração",
        "search_specialist_subagent": "Especialista de Busca",
        "idea_refiner_subagent": "Gerente de Curadoria",
    }

    def extract_messages(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        """
        Extracts combined text from the last AI turn.
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

        ai_messages = [
            m for m in current_turn_msgs if hasattr(m, "type") and m.type == "ai"
        ]

        full_text = []
        last_friendly_name = "Supervisor"

        for msg in ai_messages:
            content = msg.content
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

            r_name = getattr(msg, "name", "system") or "system"
            if r_name != "system":
                last_friendly_name = self.AGENT_NAME_MAPPING.get(r_name, r_name)

        return {
            "text": "\n\n".join(full_text).strip(),
            "agent_name": last_friendly_name,
        }

    async def extract_structured_data(
        self,
        state_values: Dict[str, Any],
        result_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        SIMPLIFIED: Returns data directly from state if available.
        Only fallbacks to parsing if we are in an interrupt state (Proposal phase).
        """
        data = {}

        # Helper to only add if truthy
        def add_if_any(key, val):
            if val:
                data[key] = val

        add_if_any("suggested_articles", state_values.get("suggested_articles"))
        add_if_any("selected_articles", state_values.get("selected_articles"))
        add_if_any("roadmap", state_values.get("roadmap"))
        add_if_any("todos", state_values.get("todos"))
        add_if_any("project_title", state_values.get("project_title"))
        add_if_any("abstract", state_values.get("abstract"))

        # Logical override: if selected exists, hide suggestions
        if data.get("selected_articles") and "suggested_articles" in data:
            del data["suggested_articles"]

        # FALLBACK: If we are in an INTURRUPT, extract the PROPOSAL from the tool call
        # This is needed because the state isn't updated yet when the graph pauses for HIL.
        if result_data and result_data.get("type") == "interrupt":
            intr_val = result_data.get("interrupts")
            if isinstance(intr_val, dict) and "action_requests" in intr_val:
                for req in intr_val["action_requests"]:
                    if req["name"] == "create_project_and_roadmap":
                        data["roadmap"] = req["args"].get("tasks", [])
                        data["project_title"] = req["args"].get("title", "")
                        data["abstract"] = req["args"].get("abstract", "")
                    elif req["name"] == "suggest_articles_to_user":
                        # The "selected_articles" proposal
                        data["selected_articles"] = req["args"].get("articles", [])

        return data

    async def chat(
        self,
        message: str,
        conversation_id: str,
        context: Optional[Dict] = None,
        search_source: str = "semantic_scholar",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        initial_state = {"messages": [HumanMessage(content=message)]}
        if user_id:
            initial_state["user_id"] = user_id

        config = {
            "configurable": {
                "thread_id": conversation_id,
                "search_source": search_source,
            }
        }
        if self.langfuse_handler:
            config["callbacks"] = [self.langfuse_handler]

        async with get_checkpointer() as checkpointer:
            graph = get_onboarding_supervisor(checkpointer=checkpointer)
            result = await graph.ainvoke(initial_state, config=config)

            state = await graph.aget_state(config)
            is_interrupted = (
                len(state.next) > 0
                and state.tasks
                and hasattr(state.tasks[0], "interrupts")
                and state.tasks[0].interrupts
            )

            # Extract textual information
            msgs_to_parse = (
                result.get("messages", [])
                if isinstance(result, dict)
                else state.values.get("messages", [])
            )
            extracted = self.extract_messages(msgs_to_parse)

            # Build intermediate result for data extraction
            interm_result = (
                {"type": "interrupt", "interrupts": state.tasks[0].interrupts[0].value}
                if is_interrupted
                else {"type": "message"}
            )

            structured_data = await self.extract_structured_data(
                state.values, interm_result
            )

            base_res = {
                "agent_name": extracted["agent_name"],
                "message": extracted["text"],
                "structured_data": (
                    structured_data if any(structured_data.values()) else None
                ),
            }

            if is_interrupted:
                base_res.update(
                    {
                        "type": "interrupt",
                        "id": state.tasks[0].id,
                        "interrupts": interm_result["interrupts"],
                    }
                )
            else:
                base_res["type"] = "message"

            return base_res
