# IT Database Administration Support Pipeline

## Overview

This pipeline governs triage and resolution of database-related incidents, including:
- Availability outages
- Performance degradation
- Data integrity concerns
- Backup and recovery issues

It prioritizes data safety and change governance.

---

## Stage: Intake

**Description**  
Ingest database incident report and normalize details.

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
Classify issue type: availability, performance, corruption, security, or maintenance.

**Allowed Agents**
- DBAClassifierAgent

**Exit Condition**
- `classification_complete(artifact)`

**Next Stages**
- Diagnosis — if `classification_complete(artifact)`
- Clarification — if `classification_ambiguous(artifact)`

---

## Stage: Clarification

**Description**  
Request missing SQL errors, query samples, metrics, or schema details.

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
Analyze query plans, locks, replication status, disk I/O, and logs.  
No data-mutating actions allowed.

**Allowed Agents**
- DBADiagnosticAgent

**Exit Condition**
- `root_cause_identified(artifact)`

**Next Stages**
- Remediation — if `root_cause_identified(artifact)`
- Escalation — if `requires_escalation(artifact)`

---

## Stage: Remediation

**Description**  
Propose remediation steps such as:
- Index changes
- Configuration adjustments
- Failover or restore plans

**Allowed Agents**
- DBARemediationAgent

**Exit Condition**
- `remediation_plan_ready(artifact)`

**Next Stages**
- Validation — if `remediation_plan_ready(artifact)`
- Escalation — if `remediation_risky(artifact)`

---

## Stage: Validation

**Description**  
Validate remediation plan against data safety, backup status, and rollback capability.

**Allowed Agents**
- DBAValidatorAgent

**Exit Condition**
- `artifact_is_valid(artifact)`

**Next Stages**
- Approval — if `artifact_is_valid(artifact)`
- Block — if `validation_failed(artifact)`

---

## Stage: Approval

**Description**  
Explicit approval required before executing any data-affecting change.

**Allowed Agents**
- ApprovalAgent

**Exit Condition**
- `hitl_approved == True`

**Next Stages**
- Resolution

---

## Stage: Resolution

**Description**  
Execute approved remediation and verify data integrity and performance.

**Allowed Agents**
- DBAExecutionAgent

**Exit Condition**
- `issue_resolved(artifact)`

**Next Stages**
- Closure — if `issue_resolved(artifact)`
- Escalation — if `resolution_failed(artifact)`

---

## Stage: Escalation

**Description**  
Escalate to senior DBAs, architects, or vendor support.

**Allowed Agents**
- EscalationAgent

**Exit Condition**
- `False`

**Terminal**
- true

---

## Stage: Closure

**Description**  
Document root cause, resolution steps, and preventative actions.

**Terminal**
- true

---

## Extraction Contract (DO NOT REMOVE)

LLM Extraction Prompt:
Extract this pipeline into a JSON object following the standard pipeline schema.

