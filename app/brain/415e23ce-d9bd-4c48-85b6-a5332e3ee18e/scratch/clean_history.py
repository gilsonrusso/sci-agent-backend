import asyncio
from app.infrastructure.ai.checkpointer import get_checkpointer
from app.agents.sub_agents.supervisor import get_onboarding_supervisor

async def main():
    thread_id = "235e3d68-3e56-408c-9882-1023f9d4686f"
    config = {"configurable": {"thread_id": thread_id}}
    
    async with get_checkpointer() as checkpointer:
        graph = get_onboarding_supervisor(checkpointer=checkpointer)
        state = await graph.aget_state(config)
        
        messages = state.values.get("messages", [])
        print(f"Total messages before: {len(messages)}")
        
        # Keep messages up to index 78. Remove anything from 79 onwards.
        from langchain_core.messages import RemoveMessage
        
        if len(messages) > 79:
            messages_to_remove = messages[79:]
            remove_commands = [RemoveMessage(id=m.id) for m in messages_to_remove if hasattr(m, "id")]
            
            await graph.aupdate_state(config, {"messages": remove_commands})
            print(f"Sent {len(remove_commands)} RemoveMessage commands.")
        else:
            print("No need to clean, message count is less than 80.")

if __name__ == "__main__":
    asyncio.run(main())
