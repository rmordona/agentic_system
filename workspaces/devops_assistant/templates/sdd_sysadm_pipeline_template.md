# IT Systems Administration Support Pipeline

## Overview

This pipeline governs triage and resolution of IT support issues related to:
- Hardware
- Operating systems
- Network connectivity
- Infrastructure services

It emphasizes safety, escalation control, and auditability.

---

## Stage: Intake

**Description**  
Ingest and normalize the incoming support request.  
Ensure required metadata is present.

**Allowed Agents**
- IntakeAgent

**Exit Condition**
- `artifact_is_valid(artifact)`

**Next Stages**
- Classification — if `artifact_is_valid(artifact)`
- Clarification — if `artifact_has_missing_info(artifact)`

---

## Stage: Classification

**Description**  
Classify the issue into hardware, OS, network, or infrastructure category.  
Determine severity and potential blast radius.

**Allowed Agents**
- SysAdminClassifierAgent

**Exit Condition**
- `classification_complete(artifact)`

**Next Stages**
- Diagnosis — if `classification_complete(artifact)`
- Clarification — if `classification_ambiguous(artifact)`

---

## Stage: Clarification

**Description**  
Request missing logs, screenshots, error messages, or system details.  
May require Human-in-the-Loop (HITL).

**Allowed Agents**
- ClarificationAgent

**Exit Condition**
- `clarifications_resolved(artifact)`

**Next Stages**
- Diagnosis — if `clarifications_resolved(artifact)`
- Block — if `clarification_failed(artifact)`

---

## Stage: Diagnosis

**Description**  
Analyze system state, logs, metrics, and recent changes.  
Identify root cause without applying changes.

**Allowed Agents**
- SysAdminDiagnosticAgent

**Exit Condition**
- `root_cause_identified(artifact)`

**Next Stages**
- Remediation — if `root_cause_identified(artifact)`
- Escalation — if `requires_escalation(artifact)`

---

## Stage: Remediation

**Description**  
Propose safe remediation steps (commands, config changes, reboots).  
No execution without approval.

**Allowed Agents**
- SysAdminRemediationAgent

**Exit Condition**
- `remediation_plan_ready(artifact)`

**Next Stages**
- Approval — if `remediation_plan_ready(artifact)`
- Escalation — if `remediation_risky(artifact)`

---

## Stage: Approval

**Description**  
Human or policy-based approval to execute remediation.

**Allowed Agents**
- ApprovalAgent

**Exit Condition**
- `hitl_approved == True`

**Next Stages**
- Resolution

---

## Stage: Resolution

**Description**  
Execute or guide execution of approved remediation.  
Confirm system stability.

**Allowed Agents**
- SysAdminExecutionAgent

**Exit Condition**
- `issue_resolved(artifact)`

**Next Stages**
- Closure — if `issue_resolved(artifact)`
- Escalation — if `resolution_failed(artifact)`

---

## Stage: Escalation

**Description**  
Escalate to senior engineers or external vendors.

**Allowed Agents**
- EscalationAgent

**Exit Condition**
- `False`

**Terminal**
- true

---

## Stage: Closure

**Description**  
Document resolution, lessons learned, and close the ticket.

**Terminal**
- true

---

## Extraction Contract (DO NOT REMOVE)

LLM Extraction Prompt:
Extract this pipeline into a JSON object following the standard pipeline schema.

