# SKILL.md: failure_mode_identification.md

Name: Failure Mode Identification
Purpose: Detect potential points of failure, risks, and unintended consequences in candidate proposals.
Input: Artifact containing candidate plans, specifications, and past analysis results.
Output: Structured list of failure modes per proposal.
Steps:
  1. Extract candidate proposals from the artifact.
  2. For each proposal, identify potential failure modes:
      a. Technical failures
      b. Operational issues
      c. Compliance violations
      d. Edge cases or untested scenarios
  3. Assess likelihood and severity of each failure mode.
  4. Document findings in JSON format, including mitigations if applicable.
Constraints:
  - Read-only access to artifact.
  - Do not propose new solutions; only identify risks.
  - Ensure coverage of all plausible failure scenarios.
Example Output:
{
  "proposal_failure_modes": [
    {
      "proposal": "Plan A: Approach X",
      "failure_modes": [
        {"description": "Integration with legacy system may fail", "likelihood": "medium", "severity": "high"},
        {"description": "Unexpected resource bottlenecks", "likelihood": "low", "severity": "medium"}
      ]
    },
    {
      "proposal": "Plan B: Approach Y",
      "failure_modes": [
        {"description": "Compliance documentation incomplete", "likelihood": "high", "severity": "high"},
        {"description": "User adoption risk", "likelihood": "medium", "severity": "medium"}
      ]
    }
  ]
}

