from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field


class MyTool(BaseModel):
    name: str = Field(description="The name")


llm = ChatOllama(model="qwen3.5:4b", temperature=0.3, presence_penalty=0.0)
print("Testing ChatOllama with tools...")
llm_with_tools = llm.bind_tools([MyTool])

try:
    res = llm_with_tools.invoke("Hello")
    print("Success!", res.content)
except Exception as e:
    print("Error:", e)
