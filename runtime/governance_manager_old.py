from pydantic import BaseModel
from typing import Any, Optional

class GovernanceViolation(Exception):
    """Raised when an Agent's action or output violates domain/system policies."""
    
    def __init__(self, rule_id: str, message: str, offending_data: Any = None):
        self.rule_id = rule_id
        self.message = message
        self.offending_data = offending_data
        super().__init__(self.message)

    def to_dict(self):
        return {
            "error_type": "GovernanceViolation",
            "rule_id": self.rule_id,
            "message": self.message,
            "data": self.offending_data
        }

class GovernanceManager:
    def validate_action(self, agent_schema: AgentSchema, proposed_payload: dict):
        # Example 1: Check Hard Constraints
        for constraint in agent_schema.constraints:
            if constraint.get("type") == "hard":
                # Implementation of constraint_4: "No non-JSON text"
                if "commentary" in proposed_payload:
                    raise GovernanceViolation(
                        rule_id=constraint["id"],
                        message="Constraint Violation: Output contains non-JSON commentary.",
                        offending_data=proposed_payload["commentary"]
                    )

        # Example 2: Domain-Specific Integrity
        if not proposed_payload.get("address") and agent_schema.id == "critic_agent":
             # If the critic didn't receive an address to critique
             raise GovernanceViolation(
                 rule_id="context_missing",
                 message="Critic cannot evaluate without an anchor address."
             )