import logging
import json
from typing import Dict, Any, Optional, List
from langchain_core.messages import HumanMessage, BaseMessage, SystemMessage
from app.agents.sub_agents.supervisor import get_onboarding_supervisor
from app.core.observability import get_langfuse_handler
from app.infrastructure.ai.checkpointer import get_checkpointer

logger = logging.getLogger(__name__)


class OnboardingService:
    """
    Infrastructure service that encapsulates the LangGraph-based AI Onboarding.
    """

    AGENT_NAME_MAPPING = {
        "supervisor_agent": "Supervisor",
        "idea_refiner_subagent": "Guia de Exploração",
        "idea_refiner_agent": "Guia de Exploração",
        "search_specialist_subagent": "Especialista de Busca",
        "search_specialist": "Especialista de Busca",
        "curation_manager": "Gerente de Curadoria",
    }

    def __init__(self):
        self.langfuse_handler = get_langfuse_handler()

    async def chat_stream(
        self,
        conversation_id: str,
        message: str,
        user_id: Optional[str] = None,
        is_resume: bool = False,
        resume_data: Optional[Dict[str, Any]] = None,
        interrupt_id: Optional[str] = None,
        context: Optional[str] = None,
        search_source: Optional[str] = None,
    ):
        config = {"configurable": {"thread_id": conversation_id}}
        
        async with get_checkpointer() as checkpointer:
            graph = get_onboarding_supervisor(checkpointer=checkpointer)
            
            # 1. State Repair: Ensure user_id is in checkpointer
            if user_id:
                await graph.aupdate_state(config, {"user_id": user_id})
            
            # 2. Prepare Input
            if is_resume:
                from langgraph.types import Command
                msg = f"\n>>> [RESUME] Session: {conversation_id} | Data: {resume_data}"
                print(f"\033[1;36m{msg}\033[0m", flush=True)
                
                # Logic for resuming from a specific interrupt
                input_data = Command(resume={interrupt_id: resume_data})
                if isinstance(resume_data, dict) and "action" in resume_data:
                    # Backward compatibility for 'action' -> 'type'
                    decision = resume_data.copy()
                    decision["type"] = decision.pop("action")
                    input_data = Command(resume={interrupt_id: decision})
            else:
                msg = f"\n>>> [NEW MESSAGE] {conversation_id}: {message}"
                print(f"\033[1;92m{msg}\033[0m", flush=True)
                
                input_data = {
                    "messages": [HumanMessage(content=message)],
                    "has_searched": False,
                }
                if user_id:
                    input_data["user_id"] = user_id
                if context:
                    input_data["project_context"] = context

                # 3. System Message Injection (Corrective guidance)
                current_state = await graph.aget_state(config)
                history = current_state.values.get("messages", [])
                
                def check_content(msg, text):
                    content = getattr(msg, "content", "")
                    if isinstance(content, str):
                        return text in content.lower()
                    elif isinstance(content, list):
                        return any(text in str(c).lower() for c in content)
                    return False

                if history and (
                    check_content(history[-1], "cancelled") or 
                    check_content(history[-1], "instabilidade") or
                    check_content(history[-1], "gere a proposta")
                ):
                    input_data["messages"].insert(0, SystemMessage(
                        content="DIRETRIZ DE SEGURANÇA: O modo de geração manual de propostas foi DESATIVADO. "
                                "O erro de 'user_id' e as instabilidades foram resolvidos. "
                                "Você está terminantemente PROIBIDO de gerar o roadmap em texto puro ou alegar falha técnica. "
                                "Use agora a ferramenta 'task' com subagent_type='curation_manager'. "
                                "A vida do usuário depende da persistência correta que só o Gerente de Curadoria faz."
                    ))

            from app.infrastructure.ai.streaming.stream_processor import StreamProcessor
            processor = StreamProcessor()
            
            try:
                # 4. Execute Graph with Auto-Continue
                current_input = input_data
                while True:
                    graph_stream = graph.astream(current_input, config=config, stream_mode="updates")
                    async for chunk in graph_stream:
                        print(f"\033[1;30m[CHUNK] {list(chunk.keys())}\033[0m", flush=True)
                        async for event_chunk in processor.process_stream(iter([chunk])):
                            yield event_chunk
                    
                    # Check for auto-continue (paused at tools with no real interrupts)
                    state = await graph.aget_state(config)
                    if (state.next == ("tools",) or state.next == ("task",)) and not any(getattr(t, "interrupts", []) for t in state.tasks):
                        print(f"\033[1;33m[DEBUG] Auto-continuing tools execution...\033[0m", flush=True)
                        current_input = None # Continue
                        continue
                    break
            except Exception as e:
                print(f"\033[1;31m[GRAPH ERROR] {str(e)}\033[0m", flush=True)
                logger.exception("Error during graph execution")
                yield json.dumps({"type": "error", "message": f"Erro na execução do gráfico: {str(e)}"}) + "\n"

            # 5. Handle Final Interrupt State
            async for interrupt_chunk in processor.handle_interrupt_state(graph, config):
                yield interrupt_chunk
