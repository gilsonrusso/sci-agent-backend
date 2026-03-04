import json
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.tools import tool
from app.core.llm import get_llm


@tool
def create_project_and_roadmap(title: str, abstract: str, tasks: list[dict]):
    """
    Ferramenta final que salva o projeto no banco de dados e determina o cronograma da pesquisa.
    O 'tasks' deve ser uma lista de dicionários contendo 'title', 'due_in_days' e 'description'.
    """
    # A implementação real chamaria um CRUD no banco de dados.
    # Por ora, simulamos o sucesso.
    return {
        "status": "success",
        "project": {"title": title, "abstract": abstract, "roadmap": tasks},
    }


CURATION_PROMPT = """Você é o **Curation & Project Manager** do SciAgent.
Sua função é consolidar a ideia do usuário e os artigos encontrados em um Roadmap acionável e um Projeto Formal.

Quando acionado pelo Supervisor:
1. Revise o tópico e os artigos.
2. Crie um Título profissional.
3. Crie um Resumo (Abstract) de ~100 palavras.
4. Crie um cronograma de 4 a 5 passos lógicos (tasks).
5. Chame a ferramenta `create_project_and_roadmap` com os dados estruturados."""


def get_curation_agent():
    # Middleware para interceptar (pausar) o fluxo
    # antes que o LLM chame a tool de salvar o projeto/roadmap.
    hil_middleware = HumanInTheLoopMiddleware(
        interrupt_on={"create_project_and_roadmap": True},
        description_prefix="Proposta de Projeto pendente de aprovação",
    )

    llm = get_llm()
    agent = create_agent(
        model=llm,
        tools=[create_project_and_roadmap],
        system_prompt=CURATION_PROMPT,
        middleware=[hil_middleware],
        name="curation_manager",
    )
    return agent
