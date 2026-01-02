# llm/stores/inmemory_store.py
from langgraph.store.base import BaseStore

from llm.stores.store_factory import StoreFactory
#from llm.base_store import BaseStore

class InMemoryStore(BaseStore):
    def __init__(self, dim: int = 1536, **kwargs):
        self.dim = dim
        self.store = {}

# register dynamically
StoreFactory.register("inmemory", InMemoryStore)

