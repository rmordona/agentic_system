# SKILL.md: governance_approval.md

Name: Governance Approval
Purpose: Provide final human or system approval for proposals, changes, or plans.
Input: Artifact containing validated proposals, spec revisions, and pipeline state.
Output: Approval decisions with rationale and metadata.
Steps:
  1. Retrieve items pending approval from the artifact.
  2. Evaluate each item against governance, policy, and compliance rules.
  3. Determine approval status:
      a. Approved
      b. Rejected
      c. Requires additional review
  4. Document decision, rationale, timestamp, and responsible approver.
  5. Update artifact with structured approval results.
Constraints:
  - Do not modify proposals or specs; only approve/reject.
  - Decisions must be auditable and traceable.
Example Output:
{
  "approvals": [
    {
      "item_id": "P1",
      "status": "approved",
      "rationale": "Meets all governance, compliance, and spec requirements",
      "approver": "ApprovalAgent",
      "timestamp": "2026-01-16T12:30:00Z"
    },
    {
      "item_id": "P2",
      "status": "rejected",
      "rationale": "Conflicts with Module X constraints",
      "approver": "ApprovalAgent",
      "timestamp": "2026-01-16T12:32:00Z"
    }
  ]
}

