# llm/chatmodels/providers.py
"""
Chat model provider registry.

Importing this module ensures that all chat model implementations
are registered with ChatModelFactory via side-effect imports.
"""

from llm.chatmodels.chatmodel_factory import ChatModelFactory

from llm.chatmodels.ollama_chatmodel import OllamaChatModel  # Ollama
#from llm.chatmodels.openai_chatmodel import OpenAIChatModel  # OpenAI
#from llm.chatmodels.anthropic_chatmodel import AnthropicChatModel  # Anthropic (Claude)
#from llm.chatmodels.cohere_chatmodel import CohereChatModel  # Cohere
#from llm.chatmodels.google_chatmodel import GoogleChatModel  # Google (Gemini / PaLM)
#from llm.chatmodels.mistral_chatmodel import MistralChatModel  # Mistral
#from llm.chatmodels.meta_chatmodel import MetaChatModel  # Meta (Llama)

# Register chat models if ready
ChatModelFactory.register("ollama", OllamaChatModel)

