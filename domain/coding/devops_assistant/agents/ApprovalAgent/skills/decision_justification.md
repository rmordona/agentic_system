# SKILL.md: decision_justification.md

Name: Decision Justification
Purpose: Provide structured, auditable reasoning for approval or rejection decisions.
Input: Artifact containing approved or rejected items.
Output: Justification report linking decisions to constraints, policies, and pipeline state.
Steps:
  1. Extract all approval/rejection decisions from the artifact.
  2. For each decision, identify:
      a. Governing rules applied
      b. Constraints or dependencies referenced
      c. Any mitigating factors or exceptions
  3. Structure reasoning in JSON format.
  4. Update artifact to include justification for downstream audit and review.
Constraints:
  - Justifications must correspond exactly to decisions made.
  - Maintain references to original items and spec sections.
  - Avoid introducing new assumptions not present in artifact.
Example Output:
{
  "decision_justifications": [
    {
      "item_id": "P1",
      "decision": "approved",
      "reasoning": "Proposal satisfies all governance policies, constraints, and spec alignment",
      "references": ["Spec Section 3.2", "Constraint Rule 7"],
      "timestamp": "2026-01-16T12:30:00Z"
    },
    {
      "item_id": "P2",
      "decision": "rejected",
      "reasoning": "Conflicts with Module X dependencies and exceeds allowed resource allocation",
      "references": ["Spec Section 4.1", "Constraint Rule 5"],
      "timestamp": "2026-01-16T12:32:00Z"
    }
  ]
}

