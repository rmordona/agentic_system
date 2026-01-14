class DisclosureState(TypedDict):
    """
    Private state for the Disclosure Agent.
    Handles summaries for human review.
    """
    summary: Optional[list[dict]]  # Summary of plan steps for HITL
    hitl_steps: Optional[list[int]]  # step_ids that require human approval
    last_disclosure_time: Optional[str]  # optional timestamp for logging

