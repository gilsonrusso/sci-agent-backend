from langchain_ollama import ChatOllama


llm_disponivie = [
    "qwen3-vl:4b",  # 3.3 GB - vision | tools | thinking
    "mistral:latest",  # 4.4 GB - tools | thinking
    "qwen3:4b",  # 2.5 GB - tools | thinking
    "mistral:7b",  # 4.4 GB - tools | thinking
    "qwen2.5-coder:7b",  # 4.7 GB - tools | thinking
]

llm = ChatOllama(
    model=llm_disponivie[0],
    format="json",
    temperature=0.2,
    stream=False,
)

response = llm.invoke("Hello, how are you?")
print(response.content)
