###########################################################################
# pipeline_template.md - Living & Dynamic SDD Pipeline Template
###########################################################################

# Overview
- Purpose: Guide agents (SkillAgent / SDDAgent) through SDD stages dynamically.
- Features:
  - Conditional stage transitions based on artifact.md / HITL signals
  - Multi-agent concurrency with merge rules
  - Dynamic exit conditions
  - Living document that can evolve with the project

---

# Stages

## Stage: Ideation
- Description: Generate initial ideas or proposals without judgment. Focused on exploration.
- Allowed Agents: PlannerAgent, OptimisticAgent
- Exit Condition: At least one valid proposal exists in artifact.md
- Next Stage(s):
  - Judgment (default)
  - Clarification (if flagged uncertainties exist)

---

## Stage: Spec_Check
- Description: Review spec.md for completeness and consistency.
- Allowed Agents: CriticAgent
- Exit Condition: All inconsistencies identified and logged
- Next Stage(s):
  - Clarification (if inconsistencies require human review)
  - Ideation (if spec revisions are required before progressing)

---

## Stage: Clarification
- Description: Ask questions to resolve spec ambiguities or missing details.
- Allowed Agents: PlannerAgent, CriticAgent
- Exit Condition: All flagged issues resolved or HITL decision recorded
- Next Stage(s):
  - Ideation (to regenerate proposals if spec changed)
  - Judgment (if clarification complete)

---

## Stage: Judgment
- Description: Evaluate proposals for conflicts, feasibility, or weakness.
- Allowed Agents: CriticAgent, SynthesizerAgent
- Exit Condition: All proposals marked as accepted, weak, or superseded
- Next Stage(s):
  - Validation (if accepted proposals exist)
  - Clarification (if critical issues detected)
  - Block (if all proposals invalid)

## Another way of formatting
- name: Judgment
  allowed_agents: ["CriticAgent", "SynthesizerAgent"]
  next_stages:
    - name: Clarification
      condition: "artifact_has_conflicts(artifact)"
    - name: Ideation
      condition: "artifact_requires_new_ideas(artifact)"
    - name: Validation
      condition: "artifact_is_valid(artifact)"

<!-- LLM Extraction Prompt: Extract this stage into a dict with keys: name, description, allowed_agents, exit_condition, next_stages (with conditions). This dict will be consumed by PipelineAdapter for dynamic routing. -->


---

## Stage: Validation
- Description: Ensure plans comply with spec.md, constitution.md, and domain constraints.
- Allowed Agents: ValidatorAgent, SkillAgent
- Exit Condition: All plans validated with violations logged
- Next Stage(s):
  - Approval (if no critical violations)
  - Clarification (if HITL review required)
  - Block (if plans violate critical constraints)

---

## Stage: Approval
- Description: Finalize the plan; mark it as ready for execution.
- Allowed Agents: SkillAgent
- Exit Condition: HITL approval received or automated checks passed
- Next Stage(s):
  - Execution (if approved)
  - Clarification (if human feedback requires changes)

---

## Stage: Block
- Description: Prevent invalid, unsafe, or non-compliant proposals from proceeding.
- Allowed Agents: CriticAgent, ValidatorAgent
- Exit Condition: All blocked items logged
- Next Stage(s):
  - Clarification (if blocked items can be fixed)
  - End (if blocked items cannot be resolved)

---

# Special Features

## Conditional Stage Transitions
- Agents dynamically choose next stage based on:
  - artifact.md contents (e.g., flagged conflicts, violations)
  - HITL decisions
  - Proposal completeness or quality metrics

## Multi-Agent Concurrency
- Multiple agents allowed in a stage may run concurrently
- Merge rules:
  - Additive proposals are merged
  - Conflicting proposals are flagged as superseded or for HITL review

## Dynamic Evolution
- Pipeline template itself is **living**:
  - New stages can be added
  - Stage transitions can be updated
  - Allowed agents list can change per iteration
- Agents interpret pipeline_template.md at runtime to **determine the current stage and next stage**

## Metadata Standard
- All agent outputs must include:
  - `agent_id`
  - `stage`
  - `timestamp` (ISO 8601)
  - `superseded` (true/false)
  - `iteration` (optional)
- Metadata ensures traceability across stages and iterations

---

# Example Dynamic Flow (illustrative)
```text
[Artifact.md] shows conflicts
Stage: Judgment
 -> Agent evaluates proposals
 -> Some proposals marked weak
 -> Conditional transition -> Clarification stage triggered
 -> PlannerAgent regenerates proposals
 -> Stage returns to Judgment
 -> Validation checks compliance
 -> Approval finalizes plan

