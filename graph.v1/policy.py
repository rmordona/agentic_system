def routing_policy(state, registry, stage_registry):
    stage = stage_registry.get(state["stage"])
    decision = stage.routing_policy(state, registry)
    if decision:
        return decision
    last = state.get("last_agent")
    if last:
        agent = registry.get(last)
        override = agent.routing_decision(state)
        if override:
            return override
    return "synthesizer"

