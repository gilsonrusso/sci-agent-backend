from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from app.agents.sub_agents.supervisor import get_onboarding_supervisor
from app.core.observability import get_langfuse_handler


class OnboardingService:
    """
    Infrastructure service that encapsulates the LangGraph-based AI Onboarding.
    """

    def __init__(self):
        self.memory_saver = MemorySaver()
        self.graph = get_onboarding_supervisor(checkpointer=self.memory_saver)
        self.langfuse_handler = get_langfuse_handler()

    async def chat(
        self,
        message: str,
        conversation_id: str,
        context: Optional[Dict] = None,
        search_source: str = "semantic_scholar",
    ) -> Dict[str, Any]:
        initial_state = {"messages": [HumanMessage(content=message)]}

        if context:
            if context.get("topic"):
                initial_state["topic"] = context["topic"]
            if context.get("selected_articles"):
                initial_state["selected_articles"] = context["selected_articles"]

        config = {
            "configurable": {
                "thread_id": conversation_id,
                "search_source": search_source,
            }
        }
        if self.langfuse_handler:
            config["callbacks"] = [self.langfuse_handler]

        result = await self.graph.ainvoke(initial_state, config=config)

        # Determine if it's an interrupt (for HIL)
        state = await self.graph.aget_state(config)
        is_interrupted = (
            len(state.next) > 0
            and len(state.tasks) > 0
            and hasattr(state.tasks[0], "interrupts")
            and state.tasks[0].interrupts
        )

        if is_interrupted:
            return {
                "type": "interrupt",
                "id": state.tasks[0].id,
                "interrupts": state.tasks[0].interrupts[0].value,
            }

        last_message = result.get("messages", [])[-1]

        # Prepare structured data for the frontend
        structured_data = {}
        vars_to_extract = [
            "suggested_articles",
            "roadmap",
            "project_title",
            "project_structure",
        ]
        for var in vars_to_extract:
            if result.get(var):
                structured_data[var] = result[var]

        return {
            "type": "message",
            "message": (
                last_message.content
                if hasattr(last_message, "content")
                else str(last_message)
            ),
            "agent_name": getattr(last_message, "name", "system") or "system",
            "structured_data": structured_data if structured_data else None,
        }
