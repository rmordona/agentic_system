import operator
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class GovernanceEngine:
    def __init__(self, policy_data: Dict[str, Any]):
        self.policy = policy_data  # Parsed from your .md or .json file
        
    def evaluate_predicates(self, ctx: Dict[str, Any], predicates: List[str]) -> bool:
        """
        Scans a list of string-based rules against the current context.
        Example: "ctx.macro_analysis.risk_index < 8"
        """
        for p in predicates:
            # In production, use a library like 'simpleeval' for safety
            # Here we use a safe-ish eval mock-up for demonstration
            try:
                # We provide 'ctx' to the evaluation environment
                if not eval(p, {"ctx": ctx, "__builtins__": {}}):
                    return False
            except Exception as e:
                print(f"Predicate failed evaluation: {p} | Error: {e}")
                return False
        return True

    def get_allowed_stages(self, current_stage_name: str, ctx: Dict[str, Any]) -> List[str]:
        """
        Scans the policy to see which gates are unlocked.
        """
        allowed = []
        current_policy = self.policy.get(current_stage_name)
        
        if not current_policy:
            return []

        # Check 'Transition Logic' from your refactored template
        for transition in current_policy.get("transition_logic", []):
            if self.evaluate_predicates(ctx, transition["if"]):
                allowed.append(transition["allow"])
                
        return allowed
