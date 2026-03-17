from typing import Any, Callable, Sequence
from langchain.agents.middleware.types import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command


class SearchResultStateMiddleware(AgentMiddleware):
    """
    Middleware that captures the results of 'execute_academic_search'
    and updates the 'suggested_articles' state field.
    """

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        result = handler(request)

        # If it's the search tool, we want to update the state
        if request.tool.name == "execute_academic_search":
            articles = []
            if isinstance(result, ToolMessage):
                import json

                try:
                    content = result.content
                    if isinstance(content, str) and (
                        content.startswith("[") or content.startswith("{")
                    ):
                        articles = json.loads(content)
                    elif isinstance(content, list):
                        articles = content
                except Exception:
                    pass

            update_data = {"messages": [result]}
            if articles:
                update_data["suggested_articles"] = articles
            else:
                update_data["suggested_articles"] = []

            # Update state silently and allow the agent to continue
            return Command(
                update=update_data,
            )

        return result

    async def awrap_tool_call(
        self, request: ToolCallRequest, handler: Callable[[ToolCallRequest], Any]
    ) -> ToolMessage | Command:
        result = await handler(request)
        return self._maybe_update_state(request, result)

    def _maybe_update_state(self, request, result):
        if request.tool.name == "execute_academic_search":
            articles = []
            if isinstance(result, ToolMessage):
                import json

                try:
                    content = result.content
                    if isinstance(content, str) and (
                        content.startswith("[") or content.startswith("{")
                    ):
                        articles = json.loads(content)
                    elif isinstance(content, list):
                        articles = content
                except Exception:
                    pass

            update_data = {"messages": [result]}
            if articles:
                update_data["suggested_articles"] = articles
            else:
                update_data["suggested_articles"] = []

            # Update state silently and allow the agent to continue
            return Command(
                update=update_data,
            )
        return result
