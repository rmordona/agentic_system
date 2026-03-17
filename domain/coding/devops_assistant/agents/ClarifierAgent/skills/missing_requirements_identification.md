# SKILL.md: missing_requirements_identification.md

Name: Missing Requirements Identification
Purpose: Detect absent or incomplete requirements in specifications.
Input: Artifact containing current specifications and proposals.
Output: Structured list of missing requirements with context.
Steps:
  1. Compare specification against expected structure or prior templates.
  2. Identify gaps, incomplete sections, or missing mandatory requirements.
  3. Document each missing requirement with location, description, and severity.
Constraints:
  - Do not modify existing spec content.
  - Only report missing elements.
  - Ensure findings are precise, actionable, and auditable.
Example Output:
{
  "missing_requirements": [
    {
      "location": "Section 2.5, Performance Metrics",
      "description": "No metrics defined for Module Z throughput",
      "severity": "high"
    },
    {
      "location": "Section 3.1, Security",
      "description": "Authentication protocol not specified",
      "severity": "medium"
    }
  ]
}

