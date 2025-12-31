from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime.memory_adapters.base import MemoryAdapter
from runtime.memory_schemas import EpisodicMemory
from runtime.memory_adapters.local_memory_store_bm25 import LocalMemoryStore


class LocalMemoryAdapter(MemoryAdapter):
    """
    Local in-memory adapter backed by BM25.
    Compatible with LangMem search & manage tools.
    """

    def __init__(
        self,
        workspace_name: str,
        persist_dir: Optional[Path] = None,
    ):
        self.workspace_name = workspace_name
        self.persist_dir = persist_dir

        self._stores: Dict[str, LocalMemoryStore] = {}

    # -----------------------------
    # Internal helpers
    # -----------------------------

    def _get_store(self, namespace: Optional[str]) -> LocalMemoryStore:
        ns = namespace or "default"

        if ns not in self._stores:
            persist_path = None
            if self.persist_dir:
                persist_path = self.persist_dir / f"{ns}.json"

            self._stores[ns] = LocalMemoryStore(
                workspace_name=self.workspace_name,
                persist_path=persist_path,
            )

        return self._stores[ns]

    def _memory_to_text(self, memory: EpisodicMemory) -> str:
        """
        What gets indexed by BM25.
        Tune this freely.
        """
        parts = [
            memory.stage,
            memory.task,
            str(memory.summary),
        ]
        return " ".join(p for p in parts if p)

    # -----------------------------
    # MemoryAdapter API
    # -----------------------------

    async def store_memory(
        self,
        memory: EpisodicMemory,
        namespace: Optional[str] = None,
    ) -> str:
        store = self._get_store(namespace)

        store.add(
            text=self._memory_to_text(memory),
            metadata=memory.dict(),
        )

        return f"{namespace or 'default'}:{len(store.data) - 1}"

    async def fetch_memory(
        self,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        stage: Optional[str] = None,
        task: Optional[str] = None,
        filter: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None,
        top_k: Optional[int] = 5,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[EpisodicMemory]:
        store = self._get_store(namespace)

        # -----------------------------
        # 1. Search
        # -----------------------------
        if query:
            results = await store.asearch(query=query, top_k=top_k or 5)
        else:
            results = store.data

        # -----------------------------
        # 2. Metadata filtering
        # -----------------------------
        def matches(meta: Dict[str, Any]) -> bool:
            if session_id and meta.get("session_id") != session_id:
                return False
            if agent and meta.get("agent") != agent:
                return False
            if stage and meta.get("stage") != stage:
                return False
            if task and meta.get("task") != task:
                return False
            if filter:
                for k, v in filter.items():
                    if meta.get(k) != v:
                        return False
            return True

        filtered = [
            r for r in results
            if matches(r["metadata"])
        ]

        # -----------------------------
        # 3. Offset + limit
        # -----------------------------
        start = offset
        end = start + (limit or top_k or 5)

        sliced = filtered[start:end]

        # -----------------------------
        # 4. Return Pydantic models
        # -----------------------------
        return [
            EpisodicMemory(**item["metadata"])
            for item in sliced
        ]

    async def asearch(
        self,
        namespace: Optional[str],
        query: str,
        offset: int = 0,
        top_k: int = 5,
        **kwargs,
    ) -> List[EpisodicMemory]:
        """
        LangMem-compatible entrypoint.
        """
        return await self.fetch_memory(
            namespace=namespace,
            query=query,
            offset=offset,
            top_k=top_k,
            **kwargs,
        )

    async def clear(
        self,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        if namespace:
            self._stores.pop(namespace, None)
        else:
            self._stores.clear()

