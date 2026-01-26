# SKILL.md: conflict_resolution.md

Name: Conflict Resolution
Purpose: Identify and resolve conflicts among proposals, plans, or specifications.
Input: Artifact containing candidate plans or proposals.
Output: Resolved plan segments with conflict annotations and decisions.
Steps:
  1. Detect conflicts between plans (timing, resources, or goals).
  2. Apply resolution strategies:
      a. Prioritization based on governance rules
      b. Re-sequencing tasks
      c. Merging overlapping elements
  3. Record decisions and justification in artifact.
Constraints:
  - Conflicts must be fully documented and traceable.
  - Must not violate safety or regulatory constraints.
Example Output:
{
  "conflict_resolutions": [
    {
      "conflict_id": "C1",
      "conflicting_plans": ["Plan1", "Plan2"],
      "resolution": "Adjusted timeline of Plan2 to avoid overlap",
      "rationale": "Plan1 has higher priority and resource allocation"
    }
  ]
}

