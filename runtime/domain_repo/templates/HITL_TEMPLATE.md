# HITL / Approval Agent Skills

## Overview
The HITL Agent ensures human oversight for high-risk or low-confidence plan steps. It pauses the orchestrator, collects approval, and updates the plan accordingly.

---

## Skills

### 1. SuspendLoop
- Description: Pause `graph.astream` loop to wait for human review.
- Inputs: summary of HITL-required steps
- Outputs: none
- Rules: Do not allow downstream execution until human responds.

### 2. CollectApproval
- Description: Present steps to the human operator for approval or modification.
- Inputs: summary
- Outputs: list of approved steps with optional notes or changes
- Rules:
  - Each HITL-required step must have an approval decision.
  - Capture notes for modifications or clarifications.

### 3. ResumeExecution
- Description: Signal the orchestrator to continue executing approved steps.
- Inputs: approved_steps
- Outputs: resume_execution: true
- Notes:
  - If modifications were made, trigger Replan Logic Agent to update the plan before execution.

### Notes
- HITL only pauses execution; it does not generate plan steps.
- Maintain strong mapping between plan.step_id and HITL decisions.
- All human decisions should be recorded for auditing and potential replanning.


