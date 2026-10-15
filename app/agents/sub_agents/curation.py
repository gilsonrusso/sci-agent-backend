from langchain_core.tools import tool
from app.core.llm import get_llm
from app.db.session import Session, engine
from app.services import project_service
from typing import Any, List, Dict, Optional, Annotated
from uuid import UUID
from deepagents import create_deep_agent
from langgraph.types import interrupt
from langgraph.prebuilt import InjectedState
from app.agents.state import OnboardingState

CURATION_PROMPT = """Você é o **Gerente de Curadoria** do SciAgent.
Sua missão é consolidar os dados do Onboarding (tema, artigos e prazo) em uma proposta formal de projeto.

### CONTEXTO DO PROJETO:
O projeto deve ser criado com base no tópico refinado, nos artigos selecionados pelo usuário e no prazo (em semanas) definido durante a conversa.

### INSTRUÇÕES DE EXECUÇÃO:
1. **Consolidação**: Use os dados disponíveis para criar um título e resumo técnicos.
2. **Roadmap**: Gere tarefas claras e sequenciais para as semanas disponíveis.
3. **Persistência**: Ao chamar `create_project_and_roadmap`, você estará disparando uma solicitação de aprovação para o usuário. 
4. **Automático**: O sistema injetará automaticamente o ID do usuário e os artigos selecionados; você não precisa se preocupar com esses campos.
5. **Confirmação**: Se o usuário aprovar, o projeto será criado permanentemente.
"""

@tool
def create_project_and_roadmap(
    title: str,
    abstract: str,
    tasks: List[Dict[str, Any]],
    state: Annotated[dict, InjectedState] = None,
    topic: Optional[str] = None,
) -> str:
    """
    Cria a proposta de projeto e o roadmap detalhado.
    Esta ferramenta interrompe a execução para aguardar a aprovação do usuário.

    Args:
        title: Título sugerido para o projeto.
        abstract: Breve resumo/objetivo do projeto.
        tasks: Lista de tarefas (roadmap). Cada tarefa deve ter 'title', 'description' e 'due_in_days'.
        topic: Tópico original da pesquisa (opcional).
    """
    user_id = state.get("user_id") if state else None
    selected_articles = state.get("selected_articles") if state else None

    # Normalização de tarefas
    normalized_tasks = []
    for i, t in enumerate(tasks or []):
        desc = t.get("description") or t.get("content") or f"Atividade da semana {i+1}"
        due = t.get("due_in_days") or (i + 1) * 7
        normalized_tasks.append({
            "title": t.get("title") or f"Tarefa {i+1}",
            "description": desc,
            "due_in_days": due
        })

    print(f"\033[1;32mDEBUG: create_project_and_roadmap | Proposta: {title} | User: {user_id}\033[0m")
    print(f"\033[1;32mDEBUG: Artigos selecionados: {len(selected_articles or [])}\033[0m")
    
    proposta_payload = {
        "title": title,
        "abstract": abstract,
        "tasks": normalized_tasks,
        "topic": topic or title,
        "user_id": user_id,
        "articles": selected_articles or []
    }
    
    try:
        # 1. Interrupção para aprovação do usuário
        print("\033[1;33mDEBUG: Disparando interrupt()...\033[0m")
        decision = interrupt(
            {
                "question": f"Deseja criar o projeto '{title}'?",
                "proposta": proposta_payload,
                "action_requests": [
                    {
                        "name": "create_project_and_roadmap",
                        "args": proposta_payload,
                        "label": "Aprovar e Criar Projeto"
                    }
                ]
            }
        )
        
        print(f"\033[1;32mDEBUG: Resposta recebida do interrupt: {decision}\033[0m")
        
        # 2. Processamento da decisão
        action = ""
        if isinstance(decision, dict):
            action = decision.get("type") or decision.get("action")
            if not action and "decisions" in decision and decision["decisions"]:
                action = decision["decisions"][0].get("type") or decision["decisions"][0].get("action")

        if action != "approve":
            print(f"\033[1;33mDEBUG: Ação não aprovada: {action}\033[0m")
            return "A criação do projeto não foi aprovada ou aguarda novos ajustes."

        # 3. Persistência Final (Somente se aprovado)
        print("\033[1;32mDEBUG: Persistindo projeto no banco...\033[0m")
        
        # Conversão de UUID segura
        owner_uuid = None
        if user_id:
            try:
                owner_uuid = UUID(user_id)
            except (ValueError, TypeError):
                print(f"\033[1;31mDEBUG: user_id inválido: {user_id}\033[0m")

        with Session(engine) as session:
            project = project_service.create_project_from_onboarding(
                session=session,
                user_id=owner_uuid,
                title=title,
                abstract=abstract,
                tasks=normalized_tasks,
                articles=selected_articles or [],
                topic=topic or title,
            )
            
        success_msg = (
            f"✅ PROJETO CRIADO COM SUCESSO!\n\n"
            f"ID: {project.id}\n"
            f"Título: {project.title}\n\n"
            f"Link para acessar: http://localhost:5173/projects/{project.id}\n\n"
            f"O Onboarding foi concluído. Você já pode começar a trabalhar no seu projeto!"
        )
        print(f"\033[1;32mDEBUG: {success_msg}\033[0m")
        return success_msg

    except Exception as e:
        # Se for GraphInterrupt, relança para o LangGraph pausar
        if e.__class__.__name__ == "GraphInterrupt":
            raise e
            
        print(f"\033[1;31mDEBUG: Erro na ferramenta: {str(e)}\033[0m")
        import traceback
        traceback.print_exc()
        return f"Erro ao processar criação: {str(e)}"

def get_curation_agent(checkpointer=None):
    return create_deep_agent(
        model=get_llm(),
        tools=[create_project_and_roadmap],
        system_prompt=CURATION_PROMPT,
        checkpointer=checkpointer,
        context_schema=OnboardingState,
        name="curation_manager",
    )
