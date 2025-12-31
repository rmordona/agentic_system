from langgraph.store.memory import InMemoryStore

# Create a local in-memory store
store = InMemoryStore(
    index={
        "dims": 1536,                 # embedding dimension
        "embed": "local",             # 'local' indicates you provide embeddings manually
    }
)
