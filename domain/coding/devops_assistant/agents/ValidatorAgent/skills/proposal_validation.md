# SKILL.md: proposal_validation.md

Name: Proposal Validation
Purpose: Validate candidate proposals against the specification and pipeline constraints.
Input: Artifact containing proposals and spec documents.
Output: Validation results including accepted and rejected proposals with rationale.
Steps:
  1. Extract all candidate proposals from the artifact.
  2. Compare each proposal against:
      a. Spec constraints
      b. Feasibility and dependencies
      c. Safety or compliance rules
  3. Record whether each proposal passes or fails validation.
  4. Include detailed reasons for rejection and any suggested adjustments.
Constraints:
  - Do not alter proposals; only validate.
  - All outputs must be JSON-compliant and traceable.
Example Output:
{
  "validated_proposals": [
    {
      "proposal_id": "P1",
      "status": "accepted",
      "reason": "Meets all spec and constraint criteria"
    },
    {
      "proposal_id": "P2",
      "status": "rejected",
      "reason": "Conflicts with Module X timing and exceeds resource limits"
    }
  ]
}

