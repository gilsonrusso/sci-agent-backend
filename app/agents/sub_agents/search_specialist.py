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
    source = config.get("configurable", {}).get("search_source", "openalex")

    if source == "openalex":
        from app.agents.tools.openalex import search_academic_papers_openalex

        return await search_academic_papers_openalex(query, limit=limit)
    else:
        from app.agents.tools.semantic_scholar import search_academic_papers_s2

        return await search_academic_papers_s2(query, limit=limit)


from typing import Any, List, Dict, Annotated
from langchain_core.tools import InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command

@tool
def suggest_articles_to_user(
    articles: List[Dict[str, Any]], 
    tool_call_id: Annotated[str, InjectedToolCallId] = None
):
    """
    IMPORTANTE: Use esta ferramenta para apresentar os artigos encontrados e pausar a execução
    para que o usuário possa selecionar quais artigos ele deseja utilizar na pesquisa.
    """
    return Command(
        update={
            "selected_articles": articles,
            "suggested_articles": [],
            "messages": [
                ToolMessage(
                    content="Artigos sugeridos com sucesso.",
                    tool_call_id=tool_call_id,
                )
            ]
        }
    )


SEARCH_SPECIALIST_PROMPT = """Você é o **Search Specialist (Especialista de Busca)** do SciAgent.
Sua função é traduzir temas de pesquisa em buscas acadêmicas rigorosas.

### REGRAS:
1. **UMA BUSCA POR VEZ**: Nunca acione a ferramenta `execute_academic_search` mais de uma vez em uma única resposta.
2. **GESTÃO DE FALHAS**:
   - Se a busca retornar erro (429) ou zero resultados, informe o Supervisor IMEDIATAMENTE.
   - Sua resposta textual final deve descrever o erro.
3. **FLUXO DE SELEÇÃO**:
    - Após a busca com sucesso e obter a lista de artigos, você DEVE chamar a ferramenta `suggest_articles_to_user` passando a lista de artigos formatada contendo 'title', 'authors', 'year', 'snippet' e 'url'.
    - Isso é obrigatório para que o sistema interrompa e mostre as opções na tela do usuário.
"""


def get_search_specialist_agent():
    from langchain.agents.middleware import HumanInTheLoopMiddleware
    return create_agent(
        model=get_llm(),
        tools=[
            execute_academic_search,
            suggest_articles_to_user,
        ],
        system_prompt=SEARCH_SPECIALIST_PROMPT,
        middleware=[
            SearchResultStateMiddleware(),
            HumanInTheLoopMiddleware(
                interrupt_on={"suggest_articles_to_user": True},
                description_prefix="Seleção de Artigos",
            )
        ],
        state_schema=OnboardingState,
        name="search_specialist",
    )
