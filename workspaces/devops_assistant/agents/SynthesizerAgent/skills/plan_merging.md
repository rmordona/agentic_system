# SKILL.md: plan_merging.md

Name: Plan Merging
Purpose: Combine multiple candidate plans or proposals into a coherent unified plan.
Input: Artifact containing multiple candidate proposals or partial plans.
Output: Merged plan with conflict resolution and rationale.
Steps:
  1. Retrieve all candidate plans from artifact.
  2. Analyze dependencies, overlaps, and conflicts.
  3. Merge plans systematically while maintaining feasibility.
  4. Document merged plan and rationale for each integration decision.
Constraints:
  - Preserve constraints and governance rules from prior stages.
  - Do not discard valid proposals without justification.
  - Maintain traceability for audit purposes.
Example Output:
{
  "merged_plan": {
    "tasks": [
      {"id": "T1", "action": "Implement Feature A", "source_plans": ["Plan1", "Plan3"]},
      {"id": "T2", "action": "Test Feature B", "source_plans": ["Plan2"]}
    ],
    "rationale": "All dependencies reconciled, no conflicts remain"
  }
}

