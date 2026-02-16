from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings

# Initialize LLM
llm = ChatOllama(
    base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL, temperature=0.7
)

# Define Prompt
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an intelligent academic writing assistant named SciAgent. "
            "You help researchers write, edit, and improve their scientific papers. "
            "The user will provide the current document content enclosed in <document_content> tags. "
            "Use this content to answer the user's request. "
            "Always be precise, academic, and helpful.",
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        (
            "user",
            "<document_content>\n{document_content}\n</document_content>\n\nRequest:\n{input}",
        ),
    ]
)

# Create Chain
writer_agent = prompt | llm | StrOutputParser()
