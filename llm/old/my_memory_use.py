from llm.store_factory import StoreFactory
from llm.memory_manager import MemoryManager
from pathlib import Path

# Load stores.json
store_factory = StoreFactory(Path("./config/stores.json"))

# Get default store
default_store = store_factory.get_store("default")

# Instantiate memory manager
memory_manager = MemoryManager(store=default_store, summarize_after=5, decay_after=20)

# Save memory
await memory_manager.save("session_123", {"prompt": "Hello", "response": "Hi!"})

# Retrieve memory
memories = await memory_manager.retrieve("session_123")
print(memories)

