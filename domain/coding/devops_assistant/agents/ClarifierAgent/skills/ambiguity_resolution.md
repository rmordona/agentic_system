# SKILL.md: ambiguity_resolution.md

Name: Ambiguity Resolution
Purpose: Resolve ambiguities or unclear points in specifications or proposals.
Input: Artifact containing specification documents, candidate proposals, or prior clarifications.
Output: Resolved specifications or clarified information with references.
Steps:
  1. Extract ambiguous statements or unclear proposals from the artifact.
  2. Analyze context and related constraints to determine clarity requirements.
  3. Generate clarification prompts or resolutions for each ambiguous item.
  4. Document the resolution or clarification in a structured format.
Constraints:
  - Only modify artifact fields with explicit permission.
  - Maintain traceability: each clarification must reference original ambiguity.
  - Do not introduce new assumptions beyond the current spec or artifact state.
Example Output:
{
  "clarifications": [
    {
      "ambiguous_item": "Requirement R3 timing",
      "clarification": "Delivery should occur within 2 weeks of milestone completion",
      "references": ["Section 3.2, Milestones"]
    },
    {
      "ambiguous_item": "Module X dependencies",
      "clarification": "Depends on Module Y completion; not Module Z",
      "references": ["Section 4.1, Dependencies"]
    }
  ]
}

