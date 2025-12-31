from sklearn.feature_extraction.text import TfidfVectorizer
from langmem import create_manage_memory_tool, create_search_memory_tool
from langgraph.store.memory import InMemoryStore
from langgraph.prebuilt import create_react_agent

from langgraph.store.postgres import AsyncPostgresStore
store = await AsyncPostgresStore.from_conn_string("postgresql://user:password@host:5432/dbname")
await store.setup()  # run migrations to set up the memory table

vectorizer = TfidfVectorizer()

'''
store = InMemoryStore(
    index={
        "dims": 1536,
        "embed": "openai:text-embedding-3-small",
    }
)
'''

# memory_managers.py
class MemoryManager:
    def __init__(self):
        self.storage = {}  # simple in-memory storage

    def store_memory(self, key, value):
        self.storage[key] = value

    def fetch_memory(self, key):
        return self.storage.get(key)

class EmbeddingsManager:
    def __init__(self):
        self.embeddings = {}  # key -> vector
        self.keys = []

    def add_embedding(self, key, embedding):
        self.embeddings[key] = embedding
        self.keys.append(key)

    def query(self, query_embedding, top_k=3):
        import numpy as np

        def cosine_sim(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10)

        sims = [(key, cosine_sim(query_embedding, self.embeddings[key])) for key in self.keys]
        sims.sort(key=lambda x: x[1], reverse=True)
        return [key for key, _ in sims[:top_k]]

def compute_embedding(text):
    return vectorizer.fit_transform([text]).toarray()[0]


memory_manager = MemoryManager()
embeddings_manager = EmbeddingsManager()

memory_tool = create_manage_memory_tool(
    name="MemoryTool", memory_manager=memory_manager
)
semantic_tool = create_search_memory_tool(
    name="SemanticTool", embeddings_manager=embeddings_manager
)


class LangMemAgentMemory:
    def __init__(self, memory_tool, semantic_tool):
        self.memory_tool = memory_tool
        self.semantic_tool = semantic_tool
        self.counter = 0

    def store(self, value):
        key = f"memory_{self.counter}"
        self.counter += 1
        self.memory_tool.store_memory(key, value)
        embedding = compute_embedding(value)
        self.semantic_tool.embeddings_manager.add_embedding(key, embedding)

    def query(self, text, top_k=3):
        embedding = compute_embedding(text)
        keys = self.semantic_tool.query(embedding, top_k=top_k)
        return [self.memory_tool.memory_manager.fetch_memory(k) for k in keys]



class DummyLLM:
    def generate(self, prompt):
        # For demo: echo the prompt plus memory info
        return f"LLM Response based on prompt:\n{prompt}"

llm = DummyLLM()

agent = Agent(
    tools=[memory_tool, semantic_tool],
    llm=llm
)

# Set a prompt template so the agent knows how to use memory tools
agent.prompt_template = """
You are a helpful assistant with memory.
Use MemoryTool to store important facts.
Use SemanticTool to recall relevant memories.

User: {user_input}
"""
print("=== LangMem Agent Interactive Demo ===")
agent_memory = LangMemAgentMemory(memory_tool, semantic_tool)

while True:
    user_input = input("User: ")
    if user_input.lower() in ["exit", "quit"]:
        break

    # Store user input as memory automatically
    agent_memory.store(user_input)

    # Invoke agent — it will use prompt_template and tools internally
    response = agent.invoke(user_input)
    print(f"Agent: {response}")
    






