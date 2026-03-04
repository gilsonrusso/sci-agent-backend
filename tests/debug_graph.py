import asyncio
from app.api.v1.endpoints.onboarding import onboarding_graph

async def main():
    initial_state = {"messages": [("user", "ola gostaria de falar sobre machine learning na area da educacao")]}
    config = {"configurable": {"thread_id": "test-cli-uuid-xyz"}}
    
    print("Starting astream...")
    async for namespace, stream_mode, data in onboarding_graph.astream(
        initial_state,
        config=config,
        stream_mode=["messages", "updates", "custom"],
        subgraphs=True,
    ):
        print(f"[{stream_mode}] Namespace: {namespace}")
        if stream_mode == "messages":
            token, metadata = data
            if hasattr(token, 'tool_calls') and token.tool_calls:
                print(f"Tool call detected: {token.tool_calls}")
            print(f"Content: {token.content}")
        elif stream_mode == "updates":
            print(f"Update: {data}")

if __name__ == "__main__":
    asyncio.run(main())
