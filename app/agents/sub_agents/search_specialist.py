from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.tools import tool
from app.core.llm import get_llm
from langchain_core.runnables import RunnableConfig


# Wrap the API search as a formal LangChain tool
@tool
async def execute_academic_search(query: str, config: RunnableConfig, limit: int = 5):
    """
    Realiza a busca em bases da literatura acadêmica gratuitas baseadas no motor escolhido pelo usuário.
    Sempre chame esta ferramenta para buscar artigos e extrair referências antes de tomar decisões.
    """
    source = config.get("configurable", {}).get("search_source", "semantic_scholar")

    if source == "openalex":
        from app.agents.tools.openalex import search_academic_papers_openalex

        return await search_academic_papers_openalex(query, limit=limit)
    else:
        from app.agents.tools.semantic_scholar import search_academic_papers_s2

        return await search_academic_papers_s2(query, limit=limit)


SEARCH_SPECIALIST_PROMPT = """Você é o **Search Specialist (Especialista de Busca)** do SciAgent.
Sua função é traduzir descrições textuais de temas de pesquisa em buscas eficientes utilizando sua ferramenta `execute_academic_search`.

Dada a requisição do usuário (ou do Supervisor):
1. Formula a melhor string de busca possível (keywords precisas).
2. Aciona a ferramenta `execute_academic_search`.
3. Retorna um sumário do que foi encontrado para o Supervisor decidir."""


def get_search_specialist_agent():
    # Middleware para interceptar (pausar) o fluxo
    # antes que o LLM chame a tool de busca efetivamente.
    hil_middleware = HumanInTheLoopMiddleware(
        interrupt_on={"execute_academic_search": True},
        description_prefix="Busca Acadêmica pendente de aprovação",
    )

    llm = get_llm()
    agent = create_agent(
        model=llm,
        tools=[execute_academic_search],
        system_prompt=SEARCH_SPECIALIST_PROMPT,
        middleware=[hil_middleware],
        name="search_specialist",
    )
    return agent
