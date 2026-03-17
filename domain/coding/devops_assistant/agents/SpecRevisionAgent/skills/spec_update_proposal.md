# SKILL.md: spec_update_proposal.md

Name: Spec Update Proposal
Purpose: Propose modifications to the specification based on identified issues or feedback.
Input: Artifact containing current specifications, validation reports, and proposed changes.
Output: Structured list of proposed spec updates with rationale and references.
Steps:
  1. Extract issues or improvement opportunities from artifact.
  2. Determine potential modifications to resolve inconsistencies, conflicts, or gaps.
  3. Document each proposed update, including:
      a. Section of the spec to be modified
      b. Proposed change
      c. Reasoning and justification
      d. Dependencies or potential impacts
  4. Output proposals in JSON format for review or HITL approval.
Constraints:
  - Do not directly modify the spec; only propose updates.
  - Ensure traceability and auditability for all proposals.
Example Output:
{
  "spec_update_proposals": [
    {
      "section": "Section 3.2, Milestone Deadlines",
      "proposal": "Adjust delivery window from 2 weeks to 3 weeks due to resource constraints",
      "rationale": "Resource availability analysis indicates 2-week window is unrealistic",
      "impact": "May delay dependent modules"
    },
    {
      "section": "Section 4.1, Security Protocol",
      "proposal": "Add OAuth2 requirement for user authentication",
      "rationale": "Current spec lacks modern authentication guidance",
      "impact": "Requires updates in dependent modules"
    }
  ]
}

