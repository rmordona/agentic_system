from sentence_transformers import SentenceTransformer
from langgraph.store.memory import InMemoryStore

# 1️⃣ Load lightweight local model
model = SentenceTransformer("all-MiniLM-L6-v2")  # offline, small

# 2️⃣ Wrap into a callable for LangGraph
def embed_fn(texts):
    return model.encode(texts, convert_to_numpy=True)

# 3️⃣ Create InMemoryStore with local embeddings
store = InMemoryStore(
    index={
        "dims": 384,  # all-MiniLM-L6-v2 outputs 384-dimensional vectors
        "embed": embed_fn
    }
)

