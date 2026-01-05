from llm.model_manager import ModelManager
from your_models.ollama_chatmodel import OllamaChatModel

primary = OllamaChatModel(endpoint="http://localhost:11434/api/chat", model_name="qwen2.5-coder:3b")
manager = ModelManager(primary_model=primary, memory_manager=memory_manager)

output = await manager.generate(
    prompt="Write a creative idea about {{topic}}",
    inputs={"topic": "AI in education"},
    memory_key="ai_ideas",
)

