# ------------------------------
# Base class for all embedding clients
# ------------------------------
class BaseEmbeddingClient:
    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError()
