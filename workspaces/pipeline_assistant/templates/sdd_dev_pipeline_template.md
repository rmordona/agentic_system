# Spec-Driven Development Pipeline Template

## Overview

This pipeline defines the governed execution flow for a Spec-Driven Development (SDD) system.

Goals:
- Enforce correctness and constraint compliance
- Prevent premature or speculative generation
- Enable dynamic routing based on artifact state
- Support Human-in-the-Loop (HITL) escalation
- Maintain full auditability and reproducibility

---

## Stage: Spec_Check

**Description**  
Ensure `spec.md` exists, is readable, and internally consistent.  
No mutations are allowed at this stage.

**Allowed Agents**
- SpecInspectorAgent

**Exit Condition**
- `artifact_is_valid(artifact)`

**Next Stages**
- Clarification — if `artifact_has_spec_gaps(artifact)`
- Ideation — if `artifact_is_valid(artifact)`

---

## Stage: Clarification

**Description**  
Resolve ambiguities, contradictions, or missing requirements.  
May request Human-in-the-Loop (HITL) input.

**Allowed Agents**
- ClarifierAgent

**Exit Condition**
- `clarifications_resolved(artifact)`

**Next Stages**
- Ideation — if `clarifications_resolved(artifact)`
- Block — if `clarification_failed(artifact)`

---

## Stage: Ideation

**Description**  
Generate candidate plans or proposals aligned strictly with `spec.md`.  
All outputs must be written to `artifact.md` only.

**Allowed Agents**
- IdeationAgent
- OptimisticAgent

**Exit Condition**
- `len(artifact["current_plan"]) > 0`

**Next Stages**
- Judgment

---

## Stage: Judgment

**Description**  
Evaluate proposals for conflicts, feasibility, and spec alignment.

**Allowed Agents**
- CriticAgent
- SynthesizerAgent

**Exit Condition**
- `all_proposals_reviewed(artifact)`

**Next Stages**
- Validation — if `accepted_proposals_exist(artifact)`
- Clarification — if `critical_issues_detected(artifact)`
- Ideation — if `artifact_requires_new_ideas(artifact)`
- Block — if `all_proposals_invalid(artifact)`

---

## Stage: Validation

**Description**  
Validate accepted proposals against constraints, technical feasibility, and execution risk.

**Allowed Agents**
- ValidatorAgent

**Exit Condition**
- `artifact_is_valid(artifact)`

**Next Stages**
- Approval — if `artifact_is_valid(artifact)`
- Spec_Revision — if `proposal_conflicts_with_spec(artifact)`

---

## Stage: Spec_Revision

**Description**  
Propose changes to `spec.md`.  
Requires explicit Human-in-the-Loop approval before applying.

**Allowed Agents**
- SpecRevisionAgent

**Exit Condition**
- `hitl_approved == True`

**Next Stages**
- Ideation

---

## Stage: Approval

**Description**  
Final human or system approval before execution.

**Allowed Agents**
- ApprovalAgent

**Exit Condition**
- `hitl_approved == True`

**Next Stages**
- Terminal

---

## Stage: Block

**Description**  
Pipeline cannot proceed safely.  
Requires human intervention.

**Allowed Agents**
- SafetyAgent

**Terminal**
- true

---

## Stage: Terminal

**Description**  
Pipeline completed successfully.

**Terminal**
- true

---

## Extraction Contract (DO NOT REMOVE)

LLM Extraction Prompt:

Extract this pipeline into a single JSON object with the following schema:

{
  "stages": [
    {
      "name": string,
      "description": string,
      "allowed_agents": [string],
      "exit_condition": string | null,
      "next_stages": [
        {
          "name": string,
          "condition": string | null
        }
      ],
      "terminal": boolean
    }
  ]
}

Rules:
- Preserve stage order
- Do not invent stages
- Conditions must remain symbolic strings
- Missing fields must be normalized

