# llm/factory_registry.py

class Registry:
    def __init__(self):
        self._registry = {}

    def register(self, key: str, cls):
        if key in self._registry:
            raise ValueError(f"Key '{key}' already registered")
        self._registry[key] = cls

    def get(self, key: str):
        cls = self._registry.get(key)
        if cls is None:
            raise ValueError(f"No implementation registered for '{key}'")
        return cls

