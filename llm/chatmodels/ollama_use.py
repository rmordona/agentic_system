from langchain_core.messages import HumanMessage, SystemMessage
from llm.adapters.ollama_adapter import OllamaAdapter
from llm.adapters.langchain_message_bridge import to_ollama_messages

adapter = OllamaAdapter(
    base_url="http://localhost:11434",
    model="qwen2.5-coder:3b",
)

messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="My favorite color is blue."),
]

ollama_messages = to_ollama_messages(messages)

response = await adapter.chat(messages=ollama_messages)

print(response.content)



=====

response = await adapter.invoke(
    messages=to_ollama_messages(messages)
)


=== to convert it back


def from_ollama_message(role: str, content: str):
    if role == "system":
        return SystemMessage(content=content)
    if role == "user":
        return HumanMessage(content=content)
    if role == "assistant":
        return AIMessage(content=content)

