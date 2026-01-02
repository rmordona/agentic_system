from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
    BaseMessage,
)

def to_ollama_messages(messages: list[BaseMessage]) -> list[dict]:
    """
    Convert LangChain messages into Ollama-compatible messages.
    """
    converted = []

    for msg in messages:
        if isinstance(msg, SystemMessage):
            role = "system"
        elif isinstance(msg, HumanMessage):
            role = "user"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        else:
            raise TypeError(f"Unsupported message type: {type(msg)}")

        converted.append({
            "role": role,
            "content": msg.content,
        })

    return converted

