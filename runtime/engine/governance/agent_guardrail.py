from __future__ import annotations
from typing import Dict, Any

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")


class GovernanceViolation(Exception):

    def __init__(self, rule_id: str, message: str, offending_data: Any = None):
        self.rule_id = rule_id
        self.message = message
        self.offending_data = offending_data
        super().__init__(message)

    def to_dict(self):

        return {
            "error_type": "GovernanceViolation",
            "rule_id": self.rule_id,
            "message": self.message,
            "data": self.offending_data,
        }


class AgentGuardrail:
    """
    Runtime guardrail enforcing agent output constraints.
    """

    def validate_output(
        self,
        agent_name: str,
        output_payload: Dict[str, Any],
        agent_schema: Dict[str, Any],
    ):

        logger.info(f"Validating output for agent '{agent_name}'")

        constraints = agent_schema.get("constraints", [])

        for rule in constraints:

            rule_type = rule.get("type")
            rule_id = rule.get("id")

            if rule_type == "hard":

                if rule.get("require_json") and not isinstance(output_payload, dict):

                    raise GovernanceViolation(
                        rule_id=rule_id,
                        message="Agent output must be JSON",
                        offending_data=output_payload,
                    )

                if rule.get("no_commentary"):

                    if "commentary" in output_payload:

                        raise GovernanceViolation(
                            rule_id=rule_id,
                            message="Non-JSON commentary detected",
                            offending_data=output_payload["commentary"],
                        )

        logger.info(f"Agent '{agent_name}' passed guardrail validation")

    def validate_tool_usage(
        self,
        agent_name: str,
        tool_name: str,
        allowed_tools: list,
    ):

        if tool_name not in allowed_tools:

            raise GovernanceViolation(
                rule_id="tool_violation",
                message=f"Agent '{agent_name}' attempted forbidden tool '{tool_name}'",
                offending_data=tool_name,
            )
