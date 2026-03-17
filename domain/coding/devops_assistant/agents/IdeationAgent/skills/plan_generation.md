# SKILL.md: plan_generation.md

Name: Plan Generation
Purpose: Generate candidate plans aligned with the artifact and specifications.
Input: Artifact containing current spec and state.
Output: Structured list of candidate plans.
Steps:
  1. Review specification and constraints from artifact.
  2. Generate multiple feasible plans respecting constraints.
  3. Document each plan clearly with rationale.
Constraints:
  - Do not validate or approve plans; only generate.
  - Plans must conform to spec constraints.
Example Output:
{
  "candidate_plans": [
    "Plan A: Use approach X to meet requirement Y",
    "Plan B: Alternate strategy using approach Z"
  ]
}

