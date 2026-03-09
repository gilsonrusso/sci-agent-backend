from typing import Any
from deepagents import create_deep_agent, CompiledSubAgent
from app.core.llm import get_llm
from app.agents.sub_agents.idea_refiner import get_idea_refiner_agent
from app.agents.sub_agents.search_specialist import get_search_specialist_agent
from app.agents.sub_agents.curation import get_curation_agent
from app.agents.state import OnboardingState

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
SUPERVISOR_PROMPT = """Você é o **Supervisor Geral** do SciAgent, o orquestrador do Onboarding "Zero to Hero".
Sua missão é ser um mentor ativo que nunca deixa o usuário sem resposta.

### REGRAS CRÍTICAS DE COMUNICAÇÃO (EVITE RESPOSTAS VAZIAS):
1. **SEMPRE FALE**: Nunca envie uma resposta sem texto. Se você chamou um sub-agente, resuma o que ele está fazendo.
2. **REPORTE ERROS**: Se um sub-agente (como o `search_specialist`) retornar um erro (ex: Rate Limit), você **DEVE** transcrever esse erro para o usuário em tom amigável e sugerir soluções (ex: trocar de base para OpenAlex).
3. **MANTENHA O DIÁLOGO**: Se você não puder avançar de estágio, explique o motivo ao usuário (ex: "Ainda precisamos escolher os artigos antes de criar o cronograma").

### REGRAS OBRIGATÓRIAS DE FLUXO (ESTRITO):
1. **SEQUÊNCIA LINEAR**: Siga os estágios 1 -> 2 -> 3 -> 4 rigidamente.
2. **ERRO NA BUSCA**: Se houver Rate Limit, **NÃO AVANCE**. Explique o erro e aguarde o usuário.
3. **TRANSIÇÃO**:
   - Estágio 2 -> 3: Só quando houver artigos.
   - Estágio 3 -> 4: Só com artigos confirmados e prazo definido.

### OS 4 ESTÁGIOS DO ONBOARDING:
1. **Estágio 1: Ideação**: Dialogue para refinar o tema com `idea_refiner`.
2. **Estágio 2: Busca**: Use `search_specialist`. Informe claramente o resultado ou erro.
3. **Estágio 3: Seleção e Prazo**: Peça para o usuário selecionar artigos. Quando confirmado via `confirm_article_selection`, peça o prazo.
4. **Estágio 4: Roadmap e Finalização**: Use o `curation_manager`.

Lembre-se: Você é o mentor. Se algo der errado, você é quem explica e guia o usuário."""


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
        context_schema=OnboardingState,
        name="supervisor_agent",
    )
    return supervisor
