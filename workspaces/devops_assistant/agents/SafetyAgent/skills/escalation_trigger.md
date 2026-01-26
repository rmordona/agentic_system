# SKILL.md: escalation_trigger.md

Name: Escalation Trigger
Purpose: Trigger human-in-the-loop or governance escalation when safety rules are violated.
Input: Artifact containing safety alerts, pipeline state, or failed checks.
Output: Structured escalation requests with context and references.
Steps:
  1. Evaluate safety alerts in the artifact.
  2. Determine if escalation is required based on rules or severity.
  3. Document escalation request including:
      a. Reason for escalation
      b. Context from artifact
      c. Recommended actions
  4. Output JSON escalation object for downstream intervention.
Constraints:
  - Only escalate when defined thresholds or rules are breached.
  - Maintain full traceability and auditability.
Example Output:
{
  "escalations": [
    {
      "escalation_id": "E1",
      "reason": "Critical plan violates safety constraints",
      "artifact_reference": "Plan2",
      "recommended_action": "Human review required before proceeding"
    }
  ]
}

