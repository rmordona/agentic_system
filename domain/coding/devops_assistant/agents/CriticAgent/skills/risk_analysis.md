# SKILL.md: risk_analysis.md

Name: Risk Analysis
Purpose: Identify potential risks, failure points, and weaknesses in proposals.
Input: Current pipeline artifact.
Output: Structured risk report highlighting high, medium, and low risks.
Steps:
  1. Review all candidate proposals in the artifact.
  2. Identify potential operational, technical, and strategic risks.
  3. Document each risk with severity, likelihood, and impact.
Constraints:
  - Only read from the artifact; do not modify it.
  - Focus on objective risk assessment, not new proposal generation.
Example Output:
{
  "risks": [
    {"description": "Insufficient resources", "severity": "high"},
    {"description": "Scalability concerns", "severity": "medium"}
  ]
}

