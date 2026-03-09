from langchain.agents import create_agent
from langchain_core.tools import tool
from app.core.llm import get_llm
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from app.agents.state import OnboardingState
from app.agents.middleware.state_sync import SearchResultStateMiddleware


@tool
async def execute_academic_search(query: str, config: RunnableConfig, limit: int = 5):
    """
    Pesquisa artigos científicos reais (Semantic Scholar / OpenAlex).
    Acione esta ferramenta para buscar referências para o tema atual.
    O termo de busca planejado será exibido abaixo.
    """
    source = config.get("configurable", {}).get("search_source", "semantic_scholar")

    if source == "openalex":
        from app.agents.tools.openalex import search_academic_papers_openalex

        return await search_academic_papers_openalex(query, limit=limit)
    else:
        from app.agents.tools.semantic_scholar import search_academic_papers_s2

        return await search_academic_papers_s2(query, limit=limit)


@tool
def confirm_article_selection(articles: list[dict]):
    """
    IMPORTANTE: Use esta ferramenta para confirmar a seleção FINAL dos artigos pelo usuário.
    Ela salva os artigos escolhidos no estado permanente do projeto e limpa as sugestões.
    """
    return Command(
        update={
            "selected_articles": articles,
            "suggested_articles": [],
        }
    )


SEARCH_SPECIALIST_PROMPT = """Você é o **Search Specialist (Especialista de Busca)** do SciAgent.
Sua função é traduzir temas de pesquisa em buscas acadêmicas rigorosas.

### REGRAS:
1. **UMA BUSCA POR VEZ**: Nunca acione a ferramenta `execute_academic_search` mais de uma vez em uma única resposta.
2. **GESTÃO DE FALHAS**:
   - Se a busca retornar erro (429) ou zero resultados, informe o Supervisor IMEDIATAMENTE.
   - Sua resposta textual final deve descrever o erro (ex: "A busca no Semantic Scholar falhou por limite de requisições") para que o Supervisor possa avisar o usuário.
3. **FLUXO DE SELEÇÃO**:
    - Após a busca com sucesso, as referências aparecerão para o usuário.
    - Quando o usuário confirmar sua escolha, use `confirm_article_selection`.
"""


def get_search_specialist_agent():
    llm = get_llm()
    agent = create_agent(
        model=llm,
        tools=[
            execute_academic_search,
            confirm_article_selection,
        ],
        system_prompt=SEARCH_SPECIALIST_PROMPT,
        middleware=[SearchResultStateMiddleware()],
        state_schema=OnboardingState,
        name="search_specialist",
    )
    return agent
