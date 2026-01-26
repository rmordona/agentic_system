# SKILL.md: inconsistency_detection.md

Name: Inconsistency Detection
Purpose: Identify contradictions, ambiguities, or incomplete elements in specifications.
Input: Artifact containing the specification document(s) and any related pipeline outputs.
Output: Structured list of detected inconsistencies with context.
Steps:
  1. Extract spec documents from the artifact.
  2. Analyze all sections for:
      a. Contradictory statements
      b. Ambiguous requirements
      c. Missing or incomplete fields
      d. Logical inconsistencies between related sections
  3. Document each detected inconsistency with:
      - Location in the spec
      - Description of the inconsistency
      - Severity (low, medium, high)
  4. Return results in a JSON array for downstream resolution or clarification.
Constraints:
  - Only read from the artifact; do not modify it.
  - Ensure all findings are precise and actionable.
  - Do not propose solutions; only detect inconsistencies.
Example Output:
{
  "detected_inconsistencies": [
    {
      "location": "Section 2.3, Requirements Table",
      "description": "Requirement R2 contradicts R5 in timing assumptions",
      "severity": "high"
    },
    {
      "location": "Section 4.1, Constraints",
      "description": "Constraint on resource X is ambiguous: range undefined",
      "severity": "medium"
    }
  ]
}

