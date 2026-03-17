class ControlStageState(TypedDict):
    """
    Full control stage state combining all agents.
    """
    shared: SharedContract
    planner: PlannerState
    disclosure: DisclosureState
    hitl: HITLState

