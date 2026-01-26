# SKILL.md: audit_trail_documentation.md

Name: Audit Trail Documentation
Purpose: Maintain a complete, auditable record of all spec revisions and associated decisions.
Input: Artifact containing spec revisions, validation results, and change proposals.
Output: Structured audit log detailing all changes and rationale.
Steps:
  1. Extract all proposed and approved changes from the artifact.
  2. Record metadata for each change:
      a. Timestamp
      b. Responsible agent
      c. Reason for change
      d. Original and updated content
  3. Ensure all entries are immutable and traceable.
  4. Output audit log in JSON format for governance or review.
Constraints:
  - Do not alter existing logs.
  - Maintain chronological order.
  - Ensure all entries reference the relevant section of the spec.
Example Output:
{
  "audit_trail": [
    {
      "timestamp": "2026-01-16T12:00:00Z",
      "agent": "SpecRevisionAgent",
      "section": "Section 3.2, Milestone Deadlines",
      "original_content": "Delivery within 2 weeks",
      "updated_content": "Delivery within 3 weeks",
      "reason": "Resource availability constraints"
    },
    {
      "timestamp": "2026-01-16T12:05:00Z",
      "agent": "SpecRevisionAgent",
      "section": "Section 4.1, Security Protocol",
      "original_content": "No explicit authentication",
      "updated_content": "OAuth2 authentication required",
      "reason": "Security compliance enhancement"
    }
  ]
}

