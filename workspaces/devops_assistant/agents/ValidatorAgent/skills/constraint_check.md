# SKILL.md: constraint_check.md

Name: Constraint Check
Purpose: Ensure that proposals or plans comply with all defined constraints in the spec.
Input: Artifact containing proposals, plans, and specification constraints.
Output: Structured report of constraint compliance for each item.
Steps:
  1. Extract proposals or plans from the artifact.
  2. Retrieve all constraints defined in the spec.
  3. For each proposal or plan:
      a. Check compliance against every relevant constraint.
      b. Record violations or non-compliance items.
  4. Output results in JSON format for downstream action.
Constraints:
  - Do not modify proposals or the spec.
  - Provide explicit references for any violations.
  - Ensure findings are deterministic and auditable.
Example Output:
{
  "constraint_compliance": [
    {
      "proposal_id": "P1",
      "violations": [],
      "compliant": true
    },
    {
      "proposal_id": "P2",
      "violations": [
        "Exceeds maximum allowed resource allocation",
        "Dependency on incomplete Module X"
      ],
      "compliant": false
    }
  ]
}

