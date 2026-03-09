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
from typing import Annotated
from langchain_core.tools import InjectedToolArg
from langchain.agents import create_agent
from app.agents.state import OnboardingState


@tool
def create_project_and_roadmap(
    title: str,
    abstract: str,
    tasks: list[dict],
    state: Annotated[dict, InjectedToolArg],
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
            return {"status": "success", "project_id": str(project.id)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


CURATION_PROMPT = """Você é o **Gerente de Curadoria**.
Sua única tarefa agora é consolidar os artigos selecionados em uma proposta formal.

**REGRAS CRÍTICAS:**
1. Você **DEVE** chamar a ferramenta `create_project_and_roadmap` IMEDIATAMENTE após elaborar o título, resumo e tarefas.
2. Não peça aprovação verbal. A chamada da ferramenta acionará automaticamente a interface de aprovação para o usuário.
3. Seus argumentos para a ferramenta devem ser detalhados e técnicos.
"""


def get_curation_agent():
    # Usamos o middleware padrão que já funcionava para gerar interrupts
    hil_middleware = HumanInTheLoopMiddleware(
        interrupt_on={"create_project_and_roadmap": True},
        description_prefix="Proposta de Projeto",
    )

    llm = get_llm()
    return create_agent(
        model=llm,
        tools=[create_project_and_roadmap],
        system_prompt=CURATION_PROMPT,
        middleware=[hil_middleware],
        state_schema=OnboardingState,
        name="curation_manager",
    )
