class PlannerState(TypedDict):
    """
    Private state for the Planner Agent.
    Holds the generated plan and step metadata.
    """
    plan: Optional[list[dict]]  # Full JSON plan as per PLAN.md
    validated: bool  # True if plan passed schema validation
    replan_requested: bool  # Triggered by Replan Logic Agent
    last_generated: Optional[str]  # Optional string or JSON snapshot for auditing

