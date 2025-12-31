from langchain.embeddings import HuggingFaceEmbeddings
from langgraph.store.memory import InMemoryStore

# Use a lightweight local HuggingFace model
hf_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

store = InMemoryStore(
    index={
        "dims": 384,                  # match the model output
        "embed": hf_embeddings        # pass the embedding object
    }
)

