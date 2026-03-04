import asyncio
from app.api.v1.endpoints.onboarding import onboarding_graph

async def main():
    initial_state = {"messages": [("user", "ola gostaria de falar sobre machine learning na area da educacao")]}
    config = {"configurable": {"thread_id": "test-cli-uuid-xyz-12345"}}
    
    print("Starting astream...")
    async for namespace, stream_mode, data in onboarding_graph.astream(
        initial_state,
        config=config,
        stream_mode=["messages", "updates", "custom"],
        subgraphs=True,
    ):
        print(f"[{stream_mode}] Namespace: {namespace}, Data: {data}")

if __name__ == "__main__":
    asyncio.run(main())
