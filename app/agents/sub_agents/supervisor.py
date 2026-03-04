from typing import Any
from deepagents import create_deep_agent, CompiledSubAgent
from app.core.llm import get_llm
from app.agents.sub_agents.idea_refiner import get_idea_refiner_agent
from app.agents.sub_agents.search_specialist import get_search_specialist_agent
from app.agents.sub_agents.curation import get_curation_agent

# 1. Recuperamos os gráficos compilados nativos
idea_refiner = get_idea_refiner_agent()
search_specialist = get_search_specialist_agent()
curation_manager = get_curation_agent()

# 2. Convertemos para SubAgentes Compilados
idea_refiner_subagent = CompiledSubAgent(
    name="idea_refiner",
    description="Para ideias imaturas ou vagas que precisam ser espremidas na dor socrática.",
    runnable=idea_refiner,
)

search_specialist_subagent = CompiledSubAgent(
    name="search_specialist",
    description="Quando o tema já está maduro e precisamos checar a literatura acadêmica.",
    runnable=search_specialist,
)

curation_manager_subagent = CompiledSubAgent(
    name="curation_manager",
    description="Quando o usuário aprovou os artigos e o próximo passo é criar o cronograma formal.",
    runnable=curation_manager,
)

# 2. Criamos o Supervisor
SUPERVISOR_PROMPT = """Você é o **Supervisor Geral** do SciAgent.
Sua função é guiar o usuário na concepção de um projeto de pesquisa delegando tarefas para sua equipe de especialistas (sub-agentes).

Sua equipe:
1. `idea_refiner`: Para ideias imaturas ou vagas que precisam ser espremidas na dor socrática.
2. `search_specialist`: Quando o tema já está maduro e precisamos checar a literatura (artigos reais).
3. `curation_manager`: Quando o usuário aprovou os artigos/tema e o próximo passo é criar o cronograma e o projeto formal.

Fluxo:
Sempre responda ou acione um sub-agente (usando a ferramenta `task`) baseado no estágio da conversa. Você gerencia a transição de Ideia -> Busca -> Fechamento. NUNCA DEIXE de acionar um especialista se o usuário solicitar algo que eles dominam.
IMPORTANTE: Se o usuário estiver apenas dizendo "olá", "tudo bem?" ou fora de contexto científico (ex: pedindo piadas), APENAS RESPONDA DIRETAMENTE sem acionar NENHUM subagente. NUNCA invente nomes de subagentes que não estão na lista acima."""


def get_onboarding_supervisor(checkpointer=None, **kwargs):
    # O LangGraph Studio injeta um config dict na factory function
    if isinstance(checkpointer, dict):
        checkpointer = None

    llm = get_llm()

    # Passamos os CompiledSubAgent do deepagents
    subagents = [
        idea_refiner_subagent,
        search_specialist_subagent,
        curation_manager_subagent,
    ]

    supervisor = create_deep_agent(
        model=llm,
        system_prompt=SUPERVISOR_PROMPT,
        subagents=subagents,
        checkpointer=checkpointer,
        name="supervisor_agent",
    )
    return supervisor
