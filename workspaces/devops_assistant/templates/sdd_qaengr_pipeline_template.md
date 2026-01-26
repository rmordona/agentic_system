# Oracle Product Quality Engineering & Triage Pipeline

## Overview

This pipeline governs issue triage, validation, and defect lifecycle management
for Oracle product quality and system testing engineering.

It enforces:
- Deterministic reproduction
- High-fidelity bug filing
- Release-aware risk assessment
- Governance over test execution and defect escalation

---

## Stage: Intake

**Description**  
Ingest incoming defect reports, test failures, customer issues, or CI regressions.
Normalize metadata (product, version, platform, environment).

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
Classify the issue by:
- Product area
- Failure type (functional, performance, stability, security)
- Source (manual test, automation, CI, customer)

Assign preliminary severity and priority.

**Allowed Agents**
- PQEClassifierAgent

**Exit Condition**
- `classification_complete(artifact)`

**Next Stages**
- Reproduction — if `classification_complete(artifact)`
- Clarification — if `classification_ambiguous(artifact)`

---

## Stage: Clarification

**Description**  
Request missing logs, test inputs, configuration details, or environment information.
May require Human-in-the-Loop (HITL).

**Allowed Agents**
- ClarificationAgent

**Exit Condition**
- `clarifications_resolved(artifact)`

**Next Stages**
- Reproduction — if `clarifications_resolved(artifact)`
- Block — if `clarification_failed(artifact)`

---

## Stage: Reproduction

**Description**  
Attempt deterministic reproduction of the issue in a controlled environment.
Document exact steps, inputs, and expected vs actual behavior.

**Allowed Agents**
- PQEReproductionAgent

**Exit Condition**
- `reproducible == True`

**Next Stages**
- Diagnosis — if `reproducible == True`
- NonReproducible — if `reproducible == False`

---

## Stage: NonReproducible

**Description**  
Handle issues that cannot be reproduced.
Evaluate environmental variance, flaky tests, or invalid reports.

**Allowed Agents**
- PQEAnalysisAgent

**Exit Condition**
- `False`

**Terminal**
- true

---

## Stage: Diagnosis

**Description**  
Analyze logs, traces, dumps, and test artifacts to identify probable root cause.
No code changes allowed.

**Allowed Agents**
- PQEDiagnosticAgent

**Exit Condition**
- `root_cause_hypothesized(artifact)`

**Next Stages**
- BugFiling — if `root_cause_hypothesized(artifact)`
- Escalation — if `requires_escalation(artifact)`

---

## Stage: BugFiling

**Description**  
Create a high-quality defect record including:
- Repro steps
- Environment
- Logs and artifacts
- Severity, priority, and impact

Ensure compliance with Oracle bug filing standards.

**Allowed Agents**
- BugFilingAgent

**Exit Condition**
- `bug_filed == True`

**Next Stages**
- ImpactAssessment — if `bug_filed == True`

---

## Stage: ImpactAssessment

**Description**  
Assess:
- Regression risk
- Affected releases
- Customer exposure
- Workaround availability

**Allowed Agents**
- PQEImpactAgent

**Exit Condition**
- `impact_assessed(artifact)`

**Next Stages**
- ValidationPlanning — if `impact_assessed(artifact)`
- Escalation — if `high_customer_impact(artifact)`

---

## Stage: ValidationPlanning

**Description**  
Define validation and regression strategy:
- Targeted tests
- Automation updates
- Cross-platform coverage

**Allowed Agents**
- PQEValidationPlannerAgent

**Exit Condition**
- `validation_plan_ready(artifact)`

**Next Stages**
- ResolutionTracking — if `validation_plan_ready(artifact)`

---

## Stage: ResolutionTracking

**Description**  
Track fix delivery from development.
Validate fixes against defined plans once available.

**Allowed Agents**
- PQEResolutionAgent

**Exit Condition**
- `fix_validated(artifact)`

**Next Stages**
- Closure — if `fix_validated(artifact)`
- Reopen — if `fix_failed(artifact)`

---

## Stage: Reopen

**Description**  
Handle failed or incomplete fixes.
Update defect and re-enter triage loop.

**Allowed Agents**
- PQEReopenAgent

**Exit Condition**
- `False`

**Terminal**
- true

---

## Stage: Escalation

**Description**  
Escalate to development leads, architects, or release management
for critical, blocking, or systemic issues.

**Allowed Agents**
- EscalationAgent

**Exit Condition**
- `False`

**Terminal**
- true

---

## Stage: Closure

**Description**  
Finalize defect resolution.
Document root cause, fix validation results, and lessons learned.

**Terminal**
- true

---

## Extraction Contract (DO NOT REMOVE)

LLM Extraction Prompt:
Extract this pipeline into a JSON object following the standard pipeline schema.

