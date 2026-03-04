import asyncio
import json
import uuid
from langchain_core.messages import HumanMessage, AIMessageChunk
from langgraph.types import Command
from app.agents.onboarding import onboarding_graph


async def simulate_onboarding_flow():
    # Usamos um thread_id aleatório como "sessão do chat"
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    print("====================================")
    print("🤖 SIMULADOR SCIAGENT ONBOARDING")
    print("====================================\n")

    # Iníciamos com um prompt genérico que forçará o Supervisor a acionar o Idea Refiner
    initial_user_prompt = "Quero fazer um projeto de pesquisa sobre formigas."
    print(f"[Usuário] -> {initial_user_prompt}")

    initial_state = {"messages": [HumanMessage(content=initial_user_prompt)]}

    while True:
        try:
            print("\n-------------------------")
            print("⏳ Executando Grafo...")
            print("-------------------------\n")

            # Vamos iterar pela resposta em formato stream
            input_val = (
                initial_state
                if initial_state is not None
                else Command(resume={"decisions": []})
            )

            async for _, stream_mode, data in onboarding_graph.astream(
                input_val,
                config=config,
                stream_mode=["messages", "updates", "custom"],
                subgraphs=True,
            ):
                initial_state = None

                if stream_mode == "messages":
                    token, metadata = data
                    if isinstance(token, AIMessageChunk):
                        agent_source = metadata.get("lc_agent_name", "Supervisor")
                        print(token.text, end="", flush=True)

                elif stream_mode == "custom":
                    print(
                        f"\n[UX Progress - {metadata.get('lc_agent_name')}] => {data}"
                    )

                elif stream_mode == "updates":
                    for source, update in data.items():
                        if source == "__interrupt__":
                            print("\n\n" + "=" * 30)
                            print("✋ INTERRUPÇÃO DO MIDDLEWARE (H-I-T-L)")
                            print("=" * 30)

                            interrupt_info = update[0]
                            interrupt_id = interrupt_info.id
                            requests = interrupt_info.value.get("action_requests", [])

                            for req in requests:
                                print(f"Ação pendente: {req.get('description')}")
                                print(
                                    f"Parâmetros: {json.dumps(req.get('args', {}), indent=2)}"
                                )

                            print("\n1: [approve] | 2: [reject] | 3: [Sair]")
                            choice = input("\n[Usuário]: ")

                            if choice == "1":
                                decision = {"type": "approve"}
                            elif choice == "2":
                                reason = input("> ")
                                decision = {"type": "reject"}
                            else:
                                return

                            # Reatribuímos initial_state como Command
                            initial_state = Command(
                                resume={interrupt_id: {"decisions": [decision]}}
                            )
                            print("-> Retomando Stream...")
                            break

            if initial_state and isinstance(initial_state, Command):
                continue

            print("\n\n[Grafo Finalizou Execução]")

            # Se initial_state não foi recriado (não teve interrupt), é porque o agente
            # encerrou a resposta e está esperando input real do usuário.
            if initial_state is None:
                new_msg = input("\n[Usuário responda] Ou (q) para sair: ")
                if new_msg.lower() == "q":
                    break
                initial_state = {"messages": [HumanMessage(content=new_msg)]}

        except Exception as e:
            import traceback

            print(f"\n🔥 ERRO CRÍTICO no Simulador: {e}")
            traceback.print_exc()
            break


if __name__ == "__main__":
    asyncio.run(simulate_onboarding_flow())
