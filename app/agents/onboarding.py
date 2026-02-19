from typing import List, Dict, Any, Literal
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.core.config import settings
from app.agents.state import OnboardingState
from app.agents.tools.scholar_mcp import search_scholar_mcp


def node_search_references(state: OnboardingState):
    """
    Executes search tool and returns results.
    """
    topic = state.get("topic") or state["messages"][-1].content

    # Call Tool (Async)
    # We are in an async context if using ainvoke?
    # LangGraph nodes can be async.
    # But wait, our node definition was synchronous. We should make it async.
    pass


import json
from datetime import datetime, timedelta

# --- Prompts ---
SYSTEM_PROMPT = """Você é o SciAgent, um assistente especializado EXCLUSIVAMENTE em planejamento de pesquisa acadêmica e escrita científica.

Seu propósito é auxiliar na formulação, estruturação e refinamento de:
- Projetos de pesquisa
- Artigos científicos (papers)
- Dissertações
- Teses
- Revisões sistemáticas
- Ensaios teóricos acadêmicos

══════════════════════════════════
DIRETRIZES OBRIGATÓRIAS
══════════════════════════════════

1. FOCO EXCLUSIVAMENTE ACADÊMICO
- Toda solicitação deve ser enquadrada como investigação científica.
- Se o usuário pedir implementação prática (ex: "criar um app", "montar API", "fazer sistema"), você deve redirecionar para:
    • Problema de pesquisa
    • Hipótese científica
    • Lacuna na literatura
    • Contribuição esperada
- Nunca forneça instruções técnicas de engenharia fora de contexto acadêmico.

2. IDIOMA
- Responder sempre em Português do Brasil (pt-BR).
- Linguagem formal, técnica e acadêmica.

3. ABORDAGEM METODOLÓGICA
Sempre conduza a conversa para esclarecer:

• Problema de pesquisa
• Justificativa científica
• Questão de pesquisa
• Hipóteses (quando aplicável)
• Objetivos (geral e específicos)
• Metodologia (qualitativa, quantitativa, mista, experimental, estudo de caso, etc.)
• Critérios de avaliação
• Métricas
• Base teórica
• Estado da arte

4. ABORDAGEM SOCRÁTICA
Não entregue respostas prontas sem antes refinar o problema.
Faça perguntas estratégicas como:
- Qual é a lacuna identificada na literatura?
- Quais trabalhos relacionados fundamentam sua proposta?
- Qual será o desenho experimental?
- Quais variáveis serão controladas?
- Como pretende validar os resultados?

5. OBJETIVO FINAL
Conduzir o usuário até produzir:
- Título provisório
- Abstract estruturado
- Estrutura do artigo (IMRaD ou modelo adequado)
- Possível contribuição científica explícita


══════════════════════════════════
SE O INPUT NÃO FOR ACADÊMICO
══════════════════════════════════

Redirecione educadamente para o contexto científico, por exemplo:

"Para tratarmos esse tema como pesquisa científica, precisamos definir qual problema acadêmico você deseja investigar. Você pretende analisar desempenho, propor um modelo teórico ou comparar abordagens existentes?"

Nunca saia do escopo acadêmico."""

# --- LLM ---
# --- LLM ---
from app.core.llm import get_llm

llm = get_llm()

# --- Nodes ---


def node_clarify_concept(state: OnboardingState):
    """
    Analyzes the user's input.
    If vague -> Ask question.
    If specific -> Extract topic and move to search.
    """
    # FIX: If articles selected but no deadline, get deadline
    if state.get("selected_articles") and len(state["selected_articles"]) > 0:
        # Clear suggested_articles to prevent re-sending to frontend
        update = {"suggested_articles": []}

        if not state.get("deadline"):
            update["current_step"] = "process_deadline"
        else:
            update["current_step"] = "generate_roadmap"

        return update

    messages = state["messages"]
    last_message = messages[-1].content

    # Intent Classification
    classification_prompt = f"""
    Analyze the user's last message: "{last_message}".
    
    Determine if the user is:
    A) Proposing a specific research topic/area (e.g., "Machine Learning in Medicine", "I want to study X").
    B) Asking a general question or chatting (e.g., "What is a paper?", "How does this work?", "Hello").
    
    Return JSON:
    {{
        "is_research_topic": boolean, 
        "topic": "extracted CORE topic only (remove 'I want to study', 'about', etc). E.g., 'Micro Frontends'", 
        "response": "appropriate response if not a topic, else null"
    }}
    """

    try:
        response = llm.invoke(
            [
                SystemMessage(content="Classify user intent. JSON only."),
                HumanMessage(content=classification_prompt),
            ]
        )
        content = response.content.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)

        if data.get("is_research_topic"):
            # User defined a topic, move to search
            # We can optionally refine the topic here or just pass it
            return {"topic": data.get("topic"), "current_step": "search"}
        else:
            # User is chatting or asking questions
            # We stay in clarify loop
            msg = AIMessage(
                content=data.get("response")
                or "Poderia especificar melhor o tema da sua pesquisa?"
            )
            return {
                "messages": [msg],
                "current_step": "clarify",
            }

    except Exception as e:
        print(f"Classification error: {e}")
        # Fallback to clarifying if we can't parse
        return {
            "messages": [
                AIMessage(
                    content="Desculpe, não entendi. Poderia detalhar qual é o tema da sua pesquisa?"
                )
            ],
            "current_step": "clarify",
        }


async def node_search_references(state: OnboardingState):
    """
    Executes search tool and returns results.
    """
    topic = state.get("topic") or state["messages"][-1].content

    # Call Tool (Async)
    try:
        results = await search_scholar_mcp(topic)
    except Exception as e:
        print(f"MCP Search Failed: {e}")
        results = []

    msg = AIMessage(
        content=f"Eu encontrei {len(results)} artigos relevantes para '{topic}'. Por favor, selecione os que você gostaria de usar."
    )

    return {
        "messages": [msg],
        "suggested_articles": results,
        "current_step": "select_articles",
    }


def node_process_deadline(state: OnboardingState):
    """
    Asks for deadline or validates it.
    """
    messages = state["messages"]
    last_message = messages[-1].content

    # Check if we should ask or validate
    # Look at the *previous* AI message to see if we already asked
    # We need to find the last AI message
    ai_messages = [m for m in messages if isinstance(m, AIMessage)]
    # Use safe access to avoid index error if no AI message yet (unlikely)
    last_ai_message = ai_messages[-1].content if ai_messages else ""

    # Heuristic: If last AI message mentions "data" or "prazo", we probably already asked.
    # If last USER message mentions "selected" or "artigos", we definitely just arrived.

    user_just_arrived = (
        "selected" in last_message.lower() or "artigos" in last_message.lower()
    )

    if user_just_arrived:
        # First time asking
        msg = AIMessage(
            content="Ótimo! Agora, qual a data final para submissão do seu artigo? (A data não pode ser inferior a 30 dias a partir de hoje)."
        )
        return {"messages": [msg], "current_step": "wait_deadline"}

    # Validate the date provided by user
    today = datetime.now()
    prompt = f"""
    The user provided: "{last_message}".
    Today is {today.strftime('%Y-%m-%d')}.
    
    Task: Extract the deadline date mentioned by the user.
    Return ONLY a JSON object: {{"date": "YYYY-MM-DD"}}
    If the user text does not contain a clear date, return {{"date": null}}
    """

    try:
        response = llm.invoke(
            [
                SystemMessage(content="Extract date. JSON only."),
                HumanMessage(content=prompt),
            ]
        )
        content = response.content.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        extracted_date_str = data.get("date")

        if not extracted_date_str:
            msg = AIMessage(
                content="Não entendi a data. Poderia digitar no formato DD/MM/AAAA?"
            )
            return {"messages": [msg], "current_step": "wait_deadline"}

        # Python Logic Validation
        try:
            deadline_date = datetime.strptime(extracted_date_str, "%Y-%m-%d")
            min_date = today + timedelta(days=30)

            # Reset time to midnight for fair comparison
            today = today.replace(hour=0, minute=0, second=0, microsecond=0)
            min_date = min_date.replace(hour=0, minute=0, second=0, microsecond=0)

            if deadline_date < today:
                msg = AIMessage(
                    content=f"A data {deadline_date.strftime('%d/%m/%Y')} já passou. Por favor, escolha uma data futura."
                )
                return {"messages": [msg], "current_step": "wait_deadline"}

            if deadline_date < min_date:
                msg = AIMessage(
                    content=f"O prazo é muito curto (menos de 30 dias). Para um projeto científico, recomendo pelo menos até {min_date.strftime('%d/%m/%Y')}. Pode ajustar?"
                )
                return {"messages": [msg], "current_step": "wait_deadline"}

            # Valid
            return {"deadline": extracted_date_str, "current_step": "generate_roadmap"}

        except ValueError:
            msg = AIMessage(content="Formato de data inválido. Use DD/MM/AAAA.")
            return {"messages": [msg], "current_step": "wait_deadline"}

    except Exception as e:
        print(f"Date extraction error: {e}")
        return {
            "messages": [
                AIMessage(
                    content="Não entendi a data. Poderia digitar no formato DD/MM/AAAA?"
                )
            ],
            "current_step": "wait_deadline",
        }


def node_generate_roadmap(state: OnboardingState):
    """
    Generates a list of tasks (roadmap) based on deadline.
    """
    topic = state.get("topic")
    selected_articles = state.get("selected_articles", [])
    deadline = state.get("deadline", "30 days from now")

    # Generate Roadmap, Title, and Structure
    prompt = f"""Based on the research topic '{topic}', the deadline '{deadline}', and the selected articles:
    {json.dumps(selected_articles, default=str)}
    
    1. CREATE a project title (academic and concise). DO NOT use the raw user topic as the title. Make it sound professional (e.g., 'Analysis of X...').
    2. CREATE a preliminary roadmap (4-5 tasks with deadlines).
    3. CREATE a brief Abstract (100-150 words) in Portuguese.
    
    Return ONLY a JSON object with keys: "title", "roadmap" (list of objects with title, due_in_days, description), "abstract".
    """

    try:
        response = llm.invoke(
            [
                SystemMessage(content="You are a research planner. Output JSON only."),
                HumanMessage(content=prompt),
            ]
        )
        content = response.content.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)

        roadmap = data.get("roadmap", [])
        project_title = data.get("title", topic)
        project_abstract = data.get("abstract", "")

    except Exception as e:
        print(f"Error generating roadmap: {e}")
        # Fallback
        project_title = topic
        project_abstract = "Resumo pendente."
        roadmap = [
            {
                "title": "Revisão Bibliográfica",
                "due_in_days": 15,
                "description": "Ler artigos selecionados",
            },
            {
                "title": "Metodologia",
                "due_in_days": 30,
                "description": "Definir métodos",
            },
        ]

    msg = AIMessage(
        content=f"Baseado no seu tópico, sugeri o título: **{project_title}**.\n\nTambém criei um roteiro preliminar. O que acha?"
    )

    return {
        "messages": [msg],
        "roadmap": roadmap,
        "project_title": project_title,
        "project_structure": {"abstract": project_abstract},
        "current_step": "confirm",
    }


# --- Router ---


def decide_next_node(
    state: OnboardingState,
) -> Literal["search_references", "generate_roadmap", "clarify_concept", "__end__"]:
    step = state.get("current_step")

    if step == "search":
        return "search_references"
    elif step == "select_articles":
        # Wait for user frontend selection (Client breaks loop here usually, but for Graph execution...)
        # If we just returned search results, we stop and wait for user input (which comes as next invoke)
        if state.get("selected_articles"):
            return "generate_roadmap"
        return END
    elif step == "generate_roadmap":
        return "generate_roadmap"
    elif step == "confirm":
        return END
    elif step == "validate_deadline":  # Internal step
        return "generate_roadmap"  # If successful
    elif step == "process_deadline":
        return "process_deadline"
    elif step == "wait_deadline":
        return END
    elif step == "clarify":
        return END
    else:
        return "clarify_concept"  # Default loop or stop?

    return END


# --- Graph ---
workflow = StateGraph(OnboardingState)

workflow.add_node("clarify_concept", node_clarify_concept)
workflow.add_node("search_references", node_search_references)
workflow.add_node("process_deadline", node_process_deadline)
workflow.add_node("generate_roadmap", node_generate_roadmap)

workflow.set_entry_point("clarify_concept")

# Conditional Edges
workflow.add_conditional_edges(
    "clarify_concept",
    decide_next_node,
    {
        "search_references": "search_references",
        "generate_roadmap": "generate_roadmap",
        "process_deadline": "process_deadline",
        "clarify_concept": "clarify_concept",
        "__end__": END,
    },
)
workflow.add_conditional_edges(
    "process_deadline",
    decide_next_node,
    {
        "generate_roadmap": "generate_roadmap",
        "process_deadline": "process_deadline",
        "__end__": END,
    },
)

# Compile
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
onboarding_graph = workflow.compile(checkpointer=memory)
