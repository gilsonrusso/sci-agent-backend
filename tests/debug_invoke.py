import asyncio
from app.api.v1.endpoints.onboarding import onboarding_graph

async def main():
    initial_state = {"messages": [("user", "ola gostaria de falar sobre machine learning na area da educacao")]}
    config = {"configurable": {"thread_id": "test-cli-uuid-xyz-123"}}
    
    print("Starting ainvoke...")
    result = await onboarding_graph.ainvoke(initial_state, config=config)
    print("FINISHED ainvoke")
    for msg in result["messages"]:
        print(f"[{msg.type}] {msg.content}")

if __name__ == "__main__":
    asyncio.run(main())
