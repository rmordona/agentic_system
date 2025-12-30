# runtime_factory.py
from runtime.singleton_resources import SingletonResources
from runtime.runtime import Runtime

# Ensure singletons are initialized once
SingletonResources.initialize_resources()

def get_runtime(session_id: str = None, user_id: str = None) -> Runtime:
    return Runtime(
        session_id=session_id,
        user_id=user_id,
        #agent_registry=SingletonResources.agent_registry,
        #stage_registry=SingletonResources.stage_registry,
        #llm=SingletonResources.llm_client,
        #redis_adapter=SingletonResources.redis_adapter,
        #event_bus=SingletonResources.event_bus,
        #semantic_memory=SingletonResources.semantic_memory,
        #memory_manager=SingletonResources.memory_manager,
        orchestrator=SingletonResources.orchestrator,

    )

