from langchain_core.tools import tool
from langchain.agents.middleware import HumanInTheLoopMiddleware
from app.core.llm import get_llm
from app.db.session import Session, engine
from app.infrastructure.repositories.sql_project_repository import SQLProjectRepository
from app.domain.onboarding.entities import OnboardingProposta, OnboardingTask
from app.application.use_cases.onboarding.create_project_use_case import (
    CreateProjectFromOnboardingUseCase,
)
from app.infrastructure.events.event_bus import LocalEventBus
from typing import Annotated, Any, List, Dict
from langchain_core.tools import InjectedToolArg, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langchain.agents import create_agent
from langgraph.types import Command
from app.agents.state import OnboardingState


@tool
def create_project_and_roadmap(
    title: str,
    abstract: str,
    tasks: List[Dict[str, Any]],
    state: Annotated[dict, InjectedToolArg],
    tool_call_id: Annotated[str, InjectedToolCallId] = None
):
    """
    Cria o projeto formal e o roadmap no banco de dados.
    Esta ferramenta deve ser chamada assim que a proposta estiver pronta.
    """
    user_id = state.get("user_id")
    if not user_id:
        return {"status": "error", "message": "User ID missing"}

    proposta = OnboardingProposta(
        owner_id=user_id,
        title=title,
        abstract=abstract,
        topic=state.get("refined_topic") or state.get("topic") or "Sem tema",
        roadmap=[
            OnboardingTask(
                title=t.get("title", ""),
                description=t.get("description", ""),
                due_in_days=t.get("due_in_days", 7),
            )
            for t in tasks
        ],
        selected_articles=state.get("selected_articles", []),
    )

    try:
        with Session(engine) as session:
            repo = SQLProjectRepository(session)
            use_case = CreateProjectFromOnboardingUseCase(repo, LocalEventBus())
            project = use_case.execute(proposta)
            
            return f"Projeto e Roadmap criados com sucesso! ID do Projeto: {project.id}. Informe o usuário que o Onboarding foi concluído e NÃO chame esta ferramenta novamente."
    except Exception as e:
        return f"Erro ao criar projeto: {str(e)}"

CURATION_PROMPT = """Você é o **Gerente de Curadoria**.
Sua tarefa é consolidar os artigos selecionados em uma proposta formal.

**REGRAS CRÍTICAS:**
1. Você **DEVE** chamar a ferramenta `create_project_and_roadmap` com o título, resumo e tarefas elaboradas.
2. Não peça aprovação verbal antes de usar a ferramenta. A chamada acionará a interface de aprovação para o usuário.
3. Seus argumentos para a ferramenta devem ser detalhados e técnicos.
4. Ao receber a mensagem de sucesso de que o projeto foi criado, apenas comunique o usuário.
"""

def get_curation_agent():
    return create_agent(
        model=get_llm(),
        tools=[create_project_and_roadmap],
        system_prompt=CURATION_PROMPT,
        middleware=[
            HumanInTheLoopMiddleware(
                interrupt_on={"create_project_and_roadmap": True},
                description_prefix="Proposta de Projeto",
            )
        ],
        state_schema=OnboardingState,
        name="curation_manager",
    )
