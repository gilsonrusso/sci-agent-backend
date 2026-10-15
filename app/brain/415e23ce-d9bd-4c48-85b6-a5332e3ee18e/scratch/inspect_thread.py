import asyncio
import uuid
from app.infrastructure.ai.checkpointer import get_checkpointer
from app.agents.sub_agents.supervisor import get_onboarding_supervisor

async def main():
    thread_id = "235e3d68-3e56-408c-9882-1023f9d4686f"
    config = {"configurable": {"thread_id": thread_id}}
    
    async with get_checkpointer() as checkpointer:
        graph = get_onboarding_supervisor(checkpointer=checkpointer)
        state = await graph.aget_state(config)
        
        print(f"--- THREAD: {thread_id} ---")
        print(f"Next steps: {state.next}")
        
        messages = state.values.get("messages", [])
        for i, msg in enumerate(messages):
            print(f"\n[{i}] {type(msg).__name__} (ID: {getattr(msg, 'id', 'N/A')})")
            content = msg.content
            if isinstance(content, list):
                print(f"  Content: {content}")
            else:
                print(f"  Content: {content[:200]}...")
            
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                print(f"  Tool Calls: {msg.tool_calls}")

if __name__ == "__main__":
    asyncio.run(main())
