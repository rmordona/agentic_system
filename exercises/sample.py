import asyncio
from langmem import create_search_memory_tool
from runtime.memory_adapters.local_memory_adapter_bm25 import LocalMemoryAdapter
from runtime.memory_schemas import EpisodicMemory

async def main():
    # Create a local in-memory adapter
    local_mem = LocalMemoryAdapter(".")

    # Optionally, seed some memory
    await local_mem.store_memory(EpisodicMemory(
        session_id="sess1",
        agent="optimistic",
        stage="ideation",
        task="Come up with ideas",
        summary={"idea": "Build a local memory system"}
    ))

    # Create a memory search tool using our local adapter
    mem_tool = create_search_memory_tool(
        store=local_mem,  # <-- your LocalMemoryAdapter
        name="LocalMemorySearch",
        namespace="hello"
    )

    # Use the tool to fetch memories
    results = await mem_tool.arun("Retrieve recent ideation tasks")
    print("Search results:", results)

asyncio.run(main())
