from langmem import create_manage_memory_tool, create_search_memory_tool
from local_memory_store import LocalMemoryStore

# Initialize memory store
workspace_name = "research_assistant"
memory_store = LocalMemoryStore(workspace_name)

# Create memory tools for LangGraph agents
memory_saver = create_manage_memory_tool(memory_store)
memory_search = create_search_memory_tool(memory_store)
