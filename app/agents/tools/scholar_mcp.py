import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import List, Dict, Any
from app.core.config import settings


async def search_scholar_mcp(query: str) -> List[Dict[str, Any]]:
    """
    Connects to the MCP Search Server and retrieves papers.
    """
    # Define server parameters
    # Use the venv python of the MCP server
    if not settings.MCP_SERVER_SCRIPT_PATH:
        raise ValueError("MCP_SERVER_SCRIPT_PATH not set in .env")

    server_params = StdioServerParameters(
        command=settings.MCP_SERVER_PYTHON_PATH,
        args=[settings.MCP_SERVER_SCRIPT_PATH],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize connection
            await session.initialize()

            # Call the tool
            result = await session.call_tool(
                "search_academic_papers", arguments={"query": query}
            )

            # MCP returns ToolResult which contains content list
            if result.content and len(result.content) > 0:
                # The content[0].text should be the JSON string representation or just the list?
                # FastMCP returns the return value directly in text usually?
                # Let's inspect how FastMCP handles returns.
                # Actually, mcp-sdk usually serializes the return value into the content text.
                # However, our tool returns a List[Dict], so it should be JSON.
                import json

                try:
                    data = json.loads(result.content[0].text)
                    return data
                except:
                    # Fallback or error handling
                    print(f"Error parsing MCP result: {result.content[0].text}")
                    return []

            return []


# Sync wrapper for compatibility with current graph (if needed, but graph supports async)
def search_scholar_sync(query: str) -> List[Dict[str, Any]]:
    return asyncio.run(search_scholar_mcp(query))
