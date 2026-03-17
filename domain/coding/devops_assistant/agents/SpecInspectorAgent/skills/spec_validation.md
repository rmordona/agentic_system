# SKILL.md: spec_validation.md

Name: Spec Validation
Purpose: Validate completeness and consistency of specifications.
Input: Artifact containing spec documents.
Output: Issues list with inconsistencies and missing sections.
Steps:
  1. Parse all spec documents from the artifact.
  2. Detect contradictions or missing sections.
  3. Document each issue with reference location.
Constraints:
  - Read-only; do not modify spec.
Example Output:
{
  "spec_issues": ["Ambiguous requirement in section 3"],
  "missing_sections": ["Error handling not documented"],
  "inconsistencies": ["Conflicting definition in sections 2 and 5"]
}

