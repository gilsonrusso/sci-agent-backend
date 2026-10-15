import logging
import json
from typing import Any, AsyncGenerator, Dict
from langgraph.types import Command

logger = logging.getLogger(__name__)

from app.infrastructure.ai.streaming.events import (
    StreamEvent,
    TokenEvent,
    StateUpdateEvent,
    InterruptEvent,
    ErrorEvent,
)
from app.infrastructure.ai.streaming.message_parser import MessageParser
from app.infrastructure.ai.streaming.state_extractor import StateExtractor


class StreamProcessor:
    """
    Acts as the conduit between LangGraph's raw events and the Frontend.
    Filters out noise, delegates business extraction to specific parsers,
    and returns strictly typed Streaming Events via NDJSON.
    """

    def __init__(self):
        self._active_agent_name = "Supervisor"

    async def process_stream(
        self, graph_stream: AsyncGenerator[Dict[str, Any], None]
    ) -> AsyncGenerator[str, None]:
        """
        Consumes `graph.astream(...)` and yields serialized NDJSON chunks 
        for the StreamingResponse.
        """
        try:
            async for chunk in graph_stream:
                for node_name, state_update in chunk.items():
                    # Log node transition
                    msg = f"--- NODE: {node_name} ---"
                    print(f"\033[1;33m{msg}\033[0m", flush=True)
                    logger.info(msg)
                    
                    if node_name == "__interrupt__":
                        print(f"\033[1;35m[INTERRUPT DETECTED] Payload: {state_update}\033[0m", flush=True)

                    if not isinstance(state_update, dict):
                        continue

                    # 1. Parse Messages (Tokens/Agent Name)
                    msgs_to_parse = state_update.get("messages", [])
                    if msgs_to_parse:
                        if not isinstance(msgs_to_parse, list):
                            msgs_to_parse = [msgs_to_parse]

                        for m in msgs_to_parse:
                            if hasattr(m, "tool_calls") and m.tool_calls:
                                for tc in m.tool_calls:
                                    msg = f"  [TOOL CALL] {tc.get('name')} | Args: {tc.get('args')}"
                                    print(f"\033[1;36m{msg}\033[0m", flush=True)
                                    logger.info(msg)

                        # Pre-analysis: If supervisor is calling a subagent, track that agent name
                        if node_name == "supervisor_agent":
                            for m in msgs_to_parse:
                                if hasattr(m, "tool_calls") and m.tool_calls:
                                    for tc in m.tool_calls:
                                        if tc.get("name") == "task":
                                            sub_type = tc.get("args", {}).get("subagent_type")
                                            if sub_type:
                                                self._active_agent_name = MessageParser.AGENT_NAME_MAPPING.get(sub_type, sub_type)
                                                logger.info(f"[Supervisor] Delegating to: {self._active_agent_name}")

                        # Use override if we are in a 'task' node (tool execution)
                        effective_node_name = self._active_agent_name if node_name == "task" else node_name
                        
                        extracted_msg = MessageParser.parse_turn(msgs_to_parse, effective_node_name)

                        if extracted_msg["text"]:
                            logger.info(f"[{extracted_msg['agent_name']}] {extracted_msg['text'][:100]}...")
                            token_event = TokenEvent(
                                content=extracted_msg["text"],
                                agent_name=extracted_msg["agent_name"]
                            )
                            yield token_event.to_stream_chunk()

                        # Reset back to Supervisor if node finished or special case
                        if node_name != "task":
                            self._active_agent_name = "Supervisor"


                    # 2. Extract State (Any confirmed structures)
                    structured_data = StateExtractor.extract_from_state(state_update)
                    if structured_data and any(structured_data.values()):
                        logger.info(f"[StateUpdate] New structures detected: {list(structured_data.keys())}")
                        state_event = StateUpdateEvent(data=structured_data)
                        yield state_event.to_stream_chunk()

        except Exception as e:
            error_event = ErrorEvent(message=f"Stream processing error: {str(e)}")
            yield error_event.to_stream_chunk()

    async def handle_interrupt_state(
        self, graph, config: dict
    ) -> AsyncGenerator[str, None]:
        """
        Checks if the graph halted on an interrupt. If so, emits an InterruptEvent.
        """
        try:
            state = await graph.aget_state(config)
            
            # DEBUG PROFUNDO
            print(f"\033[1;34m[DEBUG] handle_interrupt_state | next: {state.next}\033[0m", flush=True)
            if state.tasks:
                for i, t in enumerate(state.tasks):
                    has_ints = hasattr(t, "interrupts") and t.interrupts
                    print(f"\033[1;34m[DEBUG] Task {i} ({t.id}): name={t.name} | interrupts={len(t.interrupts) if has_ints else 0}\033[0m", flush=True)

            is_interrupted = (
                len(state.next) > 0
                and state.tasks
                and any(hasattr(t, "interrupts") and t.interrupts for t in state.tasks)
            )

            if is_interrupted:
                print(f"\033[1;35m[StreamProcessor] Graph interrompido com sucesso. Enviando evento de interrupção...\033[0m", flush=True)
                
                # Encontrar a primeira task que tem interrupções
                target_task = next(t for t in state.tasks if hasattr(t, "interrupts") and t.interrupts)
                interrupt_val = target_task.interrupts[0].value
                
                interrupt_data = StateExtractor.extract_from_interrupt(interrupt_val)

                # Send both the base state up to the pause, and the pending interrupt proposal
                structured_data = StateExtractor.extract_combined(
                    state.values, interrupt_val=interrupt_val
                )

                # The first ActionRequest usually indicates the intent
                action = "unknown"
                if isinstance(interrupt_val, dict) and "action_requests" in interrupt_val:
                    if interrupt_val["action_requests"]:
                        action = interrupt_val["action_requests"][0]["name"]

                # Combine business data with the raw action requests for the frontend
                # We merge them so the frontend sees both 'action_requests' (for buttons)
                # and 'roadmap'/'project_title' (for visualization).
                if isinstance(interrupt_val, dict):
                    structured_data.update({
                        k: v for k, v in interrupt_val.items() 
                        if k in ["action_requests", "actionRequests", "review_configs"]
                    })

                interrupt_event = InterruptEvent(
                    id=target_task.interrupts[0].id,
                    action=action,
                    data=structured_data,
                )

                # Merge structure inside the response payload as 'structured_data' for backward compat,
                # or enforce the new schema. We inject it manually to keep the prompt happy if needed.
                event_dict = interrupt_event.model_dump()
                event_dict["structured_data"] = interrupt_event.data # Compatibility alias
                yield json.dumps(event_dict) + "\n"

        except Exception as e:
            error_event = ErrorEvent(message=f"Failed to fetch interrupt state: {str(e)}")
            yield error_event.to_stream_chunk()
