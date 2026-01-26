# Patient Intake & Clinical Triage Pipeline Template

## Overview
This pipeline defines the governed flow for patient intake, risk stratification, and treatment planning.

Initial Stage: patient_intake

### Stage: patient_intake
- **Description**: Capture patient demographics, insurance validity, and primary complaint.
- **Allowed Agents**: ["IntakeCoordinatorAgent"]
- **Exit Condition**: ctx.has_valid_insurance_and_id()
Next Stages:
- clarification — if ctx.missing_medical_history()
- triage_stratification — if ctx.intake_packet_complete()

### Stage: clarification
- **Description**: Resolve missing health records or clarify conflicting allergy/medication data.
- **Allowed Agents**: ["IntakeCoordinatorAgent", "RecordsSpecialistAgent"]
- **Exit Condition**: ctx.all_gaps_resolved()
Next Stages:
- triage_stratification — if ctx.all_gaps_resolved()
- block — if ctx.patient_non_compliant()

### Stage: triage_stratification
- **Description**: Categorize patient urgency (Acuteness) and map symptoms to medical specialties.
- **Allowed Agents**: ["TriageNurseAgent", "DiagnosticAgent"]
- **Exit Condition**: ctx.acuteness_score_assigned()
Next Stages:
- specialist_matching — if ctx.is_stable()
- emergency_routing — if ctx.is_critical()

### Stage: emergency_routing
- **Description**: Immediate escalation for life-threatening symptoms. Bypasses standard scheduling.
- **Allowed Agents**: ["EmergencyResponseAgent"]
- **Exit Condition**: ctx.er_handoff_complete()
Next Stages:
- terminal — if ctx.emergency_admitted()

### Stage: specialist_matching
- **Description**: Identify and verify availability for specialists based on triage results and insurance network.
- **Allowed Agents**: ["SchedulingAgent", "MarketAnalysisAgent"]
- **Exit Condition**: len(artifact["available_providers"]) >= 1
Next Stages:
- clinical_review

### Stage: clinical_review
- **Description**: Physician-level audit of the triage notes and proposed treatment pathway for medical necessity.
- **Allowed Agents**: ["MedicalDirectorAgent"]
- **Exit Condition**: ctx.treatment_plan_authorized()
Next Stages:
- appointment_execution — if ctx.authorized()
- triage_stratification — if ctx.re_evaluation_required()

### Stage: appointment_execution
- **Description**: Finalize appointment booking, send pre-visit instructions, and trigger EHR entry.
- **Allowed Agents**: ["SchedulingAgent"]
- **Exit Condition**: ctx.has_confirmation_number()
Next Stages:
- terminal — if ctx.appointment_confirmed()
- block — if ctx.scheduling_conflict_unresolved()

### Stage: block
- **Description**: Pipeline halted due to insurance denial, lack of specialist, or medical safety concerns.
- **Allowed Agents**: ["SafetyAgent", "ComplianceOfficerAgent"]
Next Stages:
- terminal — if ctx.case_closed()
- patient_intake — if ctx.re_intake_required()

### Stage: terminal
- **Description**: Patient handoff to clinical team complete or intake formally closed.
- **Terminal**: true
