class HITLState(TypedDict):
    """
    Private state for the HITL/Approval Agent.
    Manages approvals and loop suspension.
    """
    approved_steps: Optional[list[dict]]  # step_id + approved + optional notes
    loop_suspended: bool  # True when graph.astream is waiting for human input
    human_override: Optional[list[dict]]  # optional modifications to plan
    last_approval_time: Optional[str]  # timestamp for auditing

