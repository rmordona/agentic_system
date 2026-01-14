class SharedContract(TypedDict):
    """
    Minimal shared state across all control-stage agents.
    Contains only information that multiple agents need to read or act upon.
    """
    goal: str
    constraints: dict
    selected_strategy: Optional[str]
    assumptions: list[str]
    # Optional metadata for downstream agents
    confidence: Optional[float]  # overall confidence from Deliberation
    risk_summary: Optional[dict]  # high-level risk assessment

