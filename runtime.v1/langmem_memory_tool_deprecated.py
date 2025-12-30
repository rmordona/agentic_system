from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel

from runtime.langmem_memory import LangmemAdapter
from runtime.memory_schemas import SemanticMemory


from runtime.llm_client import chat_model  # your shared LLM
#from langmem.store import InMemoryStore

'''
local_llm = LocalLLM(
    model_name="qwen2.5-coder:3b",
    endpoint="http://localhost:11434/api/chat",
)

chat_model = LocalLLMChatModel(local_llm)


# ---------------------------------------------------------
# Singleton LangMem Adapter (semantic memory only)
# ---------------------------------------------------------

_langmem_store = InMemoryStore()

memory_adapter = LangmemAdapter(
    chat_model=chat_model,
    schemas=[SemanticSummaryMemory],
    store=_langmem_store,
)
'''

# -----------------------
# Store Memory Tool
# -----------------------
async def store_memory(memory: BaseModel) -> str:
    """
    Store a semantic memory object in LangMem.

    Typically used for:
    - SemanticSummaryMemory
    - Session-level intent / preference / fact summaries
    """
    if not isinstance(memory, BaseModel):
        raise ValueError(
            "langmem_memory_tool.store_memory expects a Pydantic BaseModel"
        )

    return await memory_adapter.store_memory(memory)


# -----------------------
# Fetch Memory Tool
# -----------------------
async def fetch_memory(
    session_id: Optional[str] = None,
    task: Optional[str] = None,
    agent: Optional[Union[str, List[str]]] = None,
    stage: Optional[Union[str, List[str]]] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Fetch semantic memories using metadata filters.

    Mirrors redis_memory_tool.fetch_memory,
    but retrieves *semantic summaries* instead of raw agent outputs.
    """
    return await memory_adapter.fetch_memory(
        session_id=session_id,
        task=task,
        agent=agent,
        stage=stage,
        limit=limit,
    )


# -----------------------
# Semantic Search Tool
# -----------------------
async def semantic_search(
    query: str,
    session_id: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Perform semantic search across session memories.

    Useful for:
    - Long conversations
    - Intent drift
    - Preference recall
    """
    return await memory_adapter.semantic_search(
        query=query,
        session_id=session_id,
        limit=limit,
    )
