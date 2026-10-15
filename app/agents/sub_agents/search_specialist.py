import asyncio
from typing import List, Dict, Any, Optional, Annotated
import logging

from deepagents import create_deep_agent
from app.core.llm import get_llm
from app.agents.state import OnboardingState
from app.agents.tools.academic_search import execute_academic_search
from app.agents.tools.tavily_search import execute_web_search
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command

logger = logging.getLogger(__name__)

@tool
def present_articles_to_user_for_selection(
    articles: List[Dict[str, Any]], 
    tool_call_id: Annotated[str, InjectedToolCallId] = None
):
    """
    ENTREGA OBRIGATÓRIA: Use esta ferramenta para exibir os artigos encontrados na tela do usuário.
    Esta ferramenta interrompe a execução e abre a interface de seleção para o usuário.
    NÃO finalize sua tarefa sem chamar esta ferramenta se houver resultados.
    """
    from langgraph.types import interrupt
    
    # We interrupt with a payload that looks like what the middleware produces 
    # to maintain consistency in the frontend/StreamProcessor
    selection_request = {
        "action_requests": [
            {
                "name": "present_articles_to_user_for_selection",
                "args": {"articles": articles},
                "description": "Selecione os artigos que deseja utilizar no seu projeto."
            }
        ]
    }
    
    # The return value of interrupt will be the resume value (the selected articles)
    decision = interrupt(selection_request)
    
    selected_articles = []
    if isinstance(decision, dict) and "decisions" in decision:
        # Format compatible with HITLResponse
        for d in decision["decisions"]:
            if d.get("type") == "approve":
                # In this specific tool, 'approve' means "these are the ones I selected"
                # The frontend should send the selected articles in the 'args' or similar
                selected_articles = d.get("args", {}).get("selected_articles", [])
    
    return Command(
        update={
            "suggested_articles": articles,
            "selected_articles": selected_articles,
            "messages": [
                ToolMessage(
                    content=f"O usuário selecionou {len(selected_articles)} artigos.",
                    tool_call_id=tool_call_id,
                )
            ]
        }
    )


SEARCH_SPECIALIST_PROMPT = """Você é o **Search Specialist (Especialista de Busca)** do SciAgent.
Sua função é traduzir temas de pesquisa em buscas acadêmicas rigorosas.

### REGRAS:
1. **UMA BUSCA POR VEZ**: Nunca acione a ferramenta `execute_academic_search` ou `execute_web_search` mais de uma vez em uma única resposta.
2. **GESTÃO DE FALHAS**:
   - Se a busca retornar erro (429) ou zero resultados, tente a ferramenta alternativa (se ainda não a usou) ou informe o Supervisor IMEDIATAMENTE.
   - Sua resposta textual final deve descrever o erro.
3. **FERRAMENTAS**:
   - `execute_academic_search`: Focada em bases científicas (Semantic Scholar/OpenAlex).
   - `execute_web_search`: Focada em busca web geral e acadêmica via Tavily.
4. **REGRA DE OURO (NÃO IGNORE)**:
    - Sua tarefa **SÓ É CONCLUÍDA** quando você chama `present_articles_to_user_for_selection`.
    - Se você encontrou artigos, **VOCÊ PRECISA** usar essa ferramenta.
    - Se você apenas responder em texto, o usuário **NÃO VERÁ** nada e sua missão falhará.
    - Formate os artigos com: 'title', 'authors' (lista), 'year', 'snippet' e 'url'.
"""

def get_search_specialist_agent(checkpointer=None):
    return create_deep_agent(
        model=get_llm(),
        tools=[
            execute_academic_search,
            execute_web_search,
            present_articles_to_user_for_selection,
        ],
        system_prompt=SEARCH_SPECIALIST_PROMPT,
        checkpointer=checkpointer,
        context_schema=OnboardingState,
        name="search_specialist_subagent",
    )

# Nota: Removida a função run_search para usar o DeepAgent diretamente via supervisor.
