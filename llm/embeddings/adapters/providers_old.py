# Import all embedding providers so they self-register
from llm.embeddings.ollama_embeddings import OllamaEmbeddingClient
from llm.embeddings.openai_embeddings import OpenAIEmbeddingClient
from llm.embeddings.cohere_embeddings import CohereEmbeddingClient
