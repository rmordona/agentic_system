# SKILL.md: heuristic_suggestion.md

Name: Heuristic Suggestion
Purpose: Generate optimistic, rule-of-thumb solutions or candidate actions for partially specified problems.
Input: Artifact containing current proposals, context, and constraints.
Output: List of heuristic-based suggestions with rationale.
Steps:
  1. Analyze current artifact state to identify gaps or opportunities.
  2. Apply heuristics and prior experience to propose candidate solutions.
  3. Evaluate potential feasibility, benefits, and risks.
  4. Document each suggestion with reasoning and confidence level.
Constraints:
  - Do not propose solutions that violate explicit constraints.
  - Suggestions are probabilistic; clearly indicate assumptions.
  - All outputs must be traceable in the artifact.
Example Output:
{
  "heuristic_suggestions": [
    {
      "suggestion": "Allocate 20% buffer to milestone timeline",
      "rationale": "Historical project delays justify buffer",
      "confidence": "high"
    },
    {
      "suggestion": "Prioritize feature X for early release",
      "rationale": "Feature X has high user impact",
      "confidence": "medium"
    }
  ]
}

