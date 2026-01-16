# Spec-Driven Development Pipeline Template

## Overview

This pipeline defines the governed execution flow for a Spec-Driven Development (SDD) system.

Goals:
- Enforce correctness and constraint compliance
- Prevent premature or speculative generation
- Enable dynamic routing based on artifact state
- Support Human-in-the-Loop (HITL) escalation
- Maintain full auditability and reproducibility

### Stage: spec_check
Description: Ensure `spec.md` exists, is readable, and internally consistent. No mutations allowed.  
Allowed Agents: ["SpecInspectorAgent"]  
Exit Condition: `artifact_is_valid(artifact)`  
Next Stages:
- clarification — if `artifact_has_spec_gaps(artifact)`
- ideation — if `artifact_is_valid(artifact)`

### Stage: clarification
Description: Resolve ambiguities, contradictions, or missing requirements. May request HITL input.  
Allowed Agents: ["ClarifierAgent"]  
Exit Condition: `clarifications_resolved(artifact)`  
Next Stages:
- ideation — if `clarifications_resolved(artifact)`
- block — if `clarification_failed(artifact)`

### Stage: ideation
Description: Generate candidate plans aligned strictly with `spec.md`. Outputs written to `artifact.md`.  
Allowed Agents: ["IdeationAgent", "OptimisticAgent"]  
Exit Condition: `len(artifact["current_plan"]) > 0`  
Next Stages:
- judgment

### Stage: judgment
Description: Evaluate proposals for conflicts, feasibility, and spec alignment.  
Allowed Agents: ["CriticAgent", "SynthesizerAgent"]  
Exit Condition: `all_proposals_reviewed(artifact)`  
Next Stages:
- validation — if `accepted_proposals_exist(artifact)`
- clarification — if `critical_issues_detected(artifact)`
- ideation — if `artifact_requires_new_ideas(artifact)`
- block — if `all_proposals_invalid(artifact)`

### Stage: validation
Description: Validate accepted proposals against constraints, feasibility, and risk.  
Allowed Agents: ["ValidatorAgent"]  
Exit Condition: `artifact_is_valid(artifact)`  
Next Stages:
- approval — if `artifact_is_valid(artifact)`
- spec_revision — if `proposal_conflicts_with_spec(artifact)`

### Stage: spec_revision
Description: Propose changes to `spec.md`. Requires HITL approval before applying.  
Allowed Agents: ["SpecRevisionAgent"]  
Exit Condition: `hitl_approved == True`  
Next Stages:
- ideation

### Stage: approval
Description: Final human or system approval before execution.  
Allowed Agents: ["ApprovalAgent"]  
Next Stages:
- terminal — if `hitl_approved == True`

### Stage: block
Description: Pipeline cannot proceed safely. Requires human intervention.  
Allowed Agents: ["SafetyAgent"]  
Next Stages:
- terminal — if `human_abort_confirmed == True`

### Stage: terminal
Description: Pipeline completed successfully or halted by governance decision.  
Terminal: true

---