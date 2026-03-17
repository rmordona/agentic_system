# SKILL.md: feasibility_check.md

Name: Feasibility Check
Purpose: Evaluate candidate proposals or plans for feasibility against constraints, resources, and real-world conditions.
Input: Artifact containing candidate proposals and specifications.
Output: Structured feasibility report per proposal.
Steps:
  1. Extract all candidate proposals from the artifact.
  2. For each proposal, evaluate:
      a. Technical feasibility
      b. Resource requirements
      c. Timeline realism
      d. Regulatory and compliance constraints
      e. Operational constraints
  3. Score feasibility (e.g., high, medium, low) and provide rationale.
  4. Document all findings in a structured JSON format.
Constraints:
  - Only read from the artifact; do not modify it.
  - Do not generate new proposals.
  - Ensure objectivity and precise reasoning.
Example Output:
{
  "proposal_feasibility": [
    {
      "proposal": "Plan A: Approach X",
      "feasibility": "high",
      "rationale": "All technical and resource constraints are satisfied."
    },
    {
      "proposal": "Plan B: Approach Y",
      "feasibility": "medium",
      "rationale": "Resource constraints may require optimization."
    }
  ]
}

