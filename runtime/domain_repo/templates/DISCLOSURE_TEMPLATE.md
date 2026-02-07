# Disclosure Agent Skills

## Overview
The Disclosure Agent receives a validated plan and prepares a human-readable summary for the HITL/Approval Agent. It selectively exposes steps based on risk, confidence, and system policies.

---

## Skills

### 1. GenerateSummary
- Description: Convert a plan JSON array into a summary suitable for human inspection.
- Inputs: plan
- Outputs: summary with fields: `step_id`, `description`, `risk_level`, `hitl_required`
- Rules:
  - Only include steps necessary for HITL review.
  - Maintain execution order for context.
  - Highlight high-risk or low-confidence steps.

### 2. FlagHITLSteps
- Description: Identify which steps require human approval.
- Inputs: plan
- Outputs: list of steps where `hitl_required: true`
- Notes: This output is passed to the HITL agent.

### Notes
- Always preserve mapping from summary steps to original plan step_id.
- Ensure summary is concise but informative for decision-making.


