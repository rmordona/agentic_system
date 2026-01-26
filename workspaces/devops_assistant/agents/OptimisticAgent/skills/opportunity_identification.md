# SKILL.md: opportunity_identification.md

Name: Opportunity Identification
Purpose: Identify latent opportunities or areas of improvement within the artifact.
Input: Artifact containing current proposals, plans, and constraints.
Output: Structured list of opportunities with reasoning.
Steps:
  1. Scan artifact for unmet goals, gaps, or underutilized resources.
  2. Identify potential improvements, optimizations, or value-adds.
  3. Document opportunity, expected impact, and prerequisites.
  4. Output in JSON format for downstream consideration.
Constraints:
  - Opportunities must be realistic and actionable.
  - Must reference relevant artifact sections.
  - Do not override decisions from prior stages.
Example Output:
{
  "opportunities": [
    {
      "opportunity": "Automate testing of Module Y",
      "expected_impact": "Reduce QA time by 15%",
      "prerequisites": "Existing test framework in place"
    },
    {
      "opportunity": "Introduce micro-optimization in computation loop",
      "expected_impact": "Improve performance by 10%",
      "prerequisites": "No regression in output accuracy"
    }
  ]
}

