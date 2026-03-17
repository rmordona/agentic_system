# SKILL.md: safety_monitoring.md

Name: Safety Monitoring
Purpose: Continuously observe pipeline state to detect safety violations or risks.
Input: Artifact containing ongoing operations, proposals, and execution data.
Output: Alerts or flags highlighting unsafe states or potential hazards.
Steps:
  1. Inspect artifact for conditions that breach defined safety rules.
  2. Evaluate severity and urgency of detected risks.
  3. Document safety alerts with references to artifact data.
  4. Output structured alerts in JSON for downstream handling.
Constraints:
  - Must not modify the artifact directly.
  - Always prioritize high-severity risks.
  - Ensure alerts are auditable.
Example Output:
{
  "safety_alerts": [
    {
      "alert_id": "S1",
      "description": "Proposed plan exceeds allowed resource limit",
      "severity": "high",
      "artifact_reference": "Plan2"
    }
  ]
}

