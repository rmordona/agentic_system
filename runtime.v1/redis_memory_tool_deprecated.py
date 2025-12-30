# runtime/redis_memory_tool.py
from typing import Any, Dict, List, Optional, Union
from runtime.redis_memory import RedisMemoryAdapter
from runtime.memory_schemas import ProposalMemory, CritiqueMemory, SynthesizerMemory, BaseModel

# This creates a single Redis adapter instance that your agents can import anywhere
memory_adapter = RedisMemoryAdapter(redis_url="redis://localhost:6379/0")


# -----------------------
# Manage Memory Tool
# -----------------------
async def store_memory(memory: BaseModel) -> str:
    """
    Store a memory object in Redis.
    Accepts ProposalMemory, CritiqueMemory, SynthesizerMemory.
    Returns the Redis key.
    """
    if not isinstance(memory, BaseModel):
        raise ValueError("manage_memory_tool expects a Pydantic BaseModel memory object")
    
    key = await memory_adapter.store_memory(memory)
    return key

# -----------------------
# Fetch Memory Tool
# -----------------------
async def fetch_memory(
    session_id: Optional[str] = None,
    task: Optional[str] = None,
    agent: Optional[Union[str, List[str]]] = None,
    stage: Optional[Union[str, List[str]]] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch stored memories filtered by task, agent, or stage.
    Returns a list of memory dicts.
    """
    return await memory_adapter.fetch_memory(
            session_id=session_id,
            task=task,
            agent=agent,
            stage=stage,
        )

