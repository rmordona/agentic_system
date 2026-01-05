"""
RuntimeContext provides a scoped, immutable view over the MemoryManager.

It binds runtime dimensions (session, agent, stage, task, namespace)
into a stable, hashable key namespace and exposes a simple API for
storing and retrieving episodic and semantic memory.

RuntimeContext contains NO storage logic.
All persistence, adapters, and backends are delegated to MemoryManager.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class RuntimeContext:
    def __init__(
        self,
        *,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        stage: Optional[str] = None,
        task: Optional[str] = None,
        top_k: Optional[int] = None,
        limit: Optional[int] = None,
    ):

        self.namespace = namespace
        self.top_k = top_k
        self.limit = limit

        # Dynamically updated during Agent.run()
        self.session_id = session_id
        self.agent = agent
        self.stage = stage
        self.task = task

        # A new key_namespace will be formed as store key
        self.key_namespace: Tuple[str, str] = None

    # ----------------------------
    # Context scoping
    # ----------------------------
    def with_session(self, session_id: str) -> "RuntimeContext":
        return RuntimeContext(
            namespace=self.namespace,
            session_id=session_id,
            agent=self.agent,
            stage=self.stage,
            task=self.task,
            top_k=self.top_k,
            limit=self.limit
        )

    def with_agent(self, agent: str) -> "RuntimeContext":
        return RuntimeContext(
            namespace=self.namespace,
            session_id=self.session_id,
            agent=agent,
            stage=self.stage,
            task=self.task,
            top_k=self.top_k,
            limit=self.limit
        )

    def with_stage(self, stage: str) -> "RuntimeContext":
        return RuntimeContext(
            namespace=self.namespace,
            session_id=self.session_id,
            agent=self.agent,
            stage=stage,
            task=self.task,
            top_k=self.top_k,
            limit=self.limit
        )

    def with_task(self, task: str) -> "RuntimeContext":
        return RuntimeContext(
            namespace=self.namespace,
            session_id=self.session_id,
            agent=self.agent,
            stage=self.stage,
            task=task,
            top_k=self.top_k,
            limit=self.limit
        )

    def with_namespace(self, namespace: str) -> "RuntimeContext":
        return RuntimeContext(
            namespace=namespace,
            session_id=self.session_id,
            agent=self.agent,
            stage=self.stage,
            task=self.task,
            top_k=self.top_k,
            limit=self.limit
        )

    def generate_key_namespace(self)  -> "RuntimeContext":
        # This Store, langgraph.store.memory import InMemoryStore, does not
        # support structured tuples (Tuple[str, str])
        '''
        self.key_namespace = (
                ("session_id",  self.session_id),
                ("agent",       self.agent),
                ("stage",       self.stage),
                ("namespace",   self.namespace) )
        '''

        # So let's use Tuple[str]
        self.key_namespace = (
                f"session_id:{self.session_id}",
                f"agent:{self.agent}",
                f"stage:{self.stage}",
                f"namespace:{self.namespace}" )
        return self

