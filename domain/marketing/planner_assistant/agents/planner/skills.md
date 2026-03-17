# Planner Agent Skills

## Overview
The Planner Agent converts a selected strategy into a structured, executable plan. Each step includes a description, tool reference, inputs, dependencies, risk assessment, confidence score, and HITL requirement.

---

## Skills

### 1. GeneratePlan
- Description: Take `goal`, `selected_strategy`, `constraints`, and `assumptions` to produce a structured JSON plan.
- Steps:
  1. Parse the selected strategy and extract candidate actions.
  2. Decompose actions into discrete, executable steps.
  3. Assign each step a `tool`, `inputs`, and `step_id`.
  4. Determine step dependencies and populate `dependencies`.
  5. Assign `risk_level` based on potential impact.
  6. Assign `confidence` score (0.0 - 1.0) for each step.
  7. Set `hitl_required: true` if confidence < `hitl_threshold` or risk is high.
  8. Output the plan as JSON array matching `PLAN.md`.

### 2. AnnotateStep
- Description: Add metadata to individual steps.
- Inputs: step description, tool, inputs
- Outputs: step with `risk_level`, `confidence`, `hitl_required`, dependencies
- Notes: Used internally during plan generation.

### 3. ValidatePlan
- Description: Ensure all steps conform to `output_schema`.
- Checks:
  - All `step_id` unique
  - All dependencies refer to existing steps
  - Tools exist in `constraints.tools_allowed`
  - JSON is fully parseable
- Output: validated plan or error

### 4. PrepareForHITL
- Description: Identify all steps that require human approval
- Inputs: validated plan
- Outputs: list of HITL steps with metadata for Disclosure Agent

---

## Notes
- Always follow `PLAN.md` format strictly.
- Ensure output is safe, reversible if possible, and suitable for execution.
- Maintain strict separation from Deliberation Agent state; only read `selected_strategy` and constraints from shared contract.
- Supports replan requests from Replan Logic Agent.

