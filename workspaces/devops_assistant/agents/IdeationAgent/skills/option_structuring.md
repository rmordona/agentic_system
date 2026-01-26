# SKILL.md: option_structuring.md

Name: Option Structuring
Purpose: Generate structured, feasible candidate options aligned with the current specification.
Input: Artifact containing validated specifications, constraints, and prior proposals.
Output: List of structured options with rationale and categorization.
Steps:
  1. Extract current spec and any existing proposals from the artifact.
  2. Identify key objectives and constraints from the spec.
  3. Generate multiple candidate options that satisfy constraints.
  4. For each option, document:
      a. Objective addressed
      b. Key assumptions
      c. Dependencies
      d. Expected outcome
  5. Structure options in a JSON array for downstream evaluation.
Constraints:
  - Do not violate constraints defined in the spec.
  - Do not overwrite existing proposals in the artifact.
  - Maintain orthogonality and diversity among options.
Example Output:
{
  "candidate_options": [
    {
      "option_name": "Option A: Incremental Approach",
      "objective": "Minimize risk while achieving baseline spec requirements",
      "assumptions": ["Resource allocation is sufficient", "Stakeholders approve incremental delivery"],
      "dependencies": ["Module X must be complete"],
      "expected_outcome": "Partial but validated delivery"
    },
    {
      "option_name": "Option B: Full-Scope Approach",
      "objective": "Deliver complete spec in one iteration",
      "assumptions": ["No unplanned blockers", "All resources available"],
      "dependencies": ["Module X and Module Y must be complete"],
      "expected_outcome": "Full delivery with higher risk"
    }
  ]
}

