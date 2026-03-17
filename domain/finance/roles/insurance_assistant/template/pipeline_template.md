# Insurance Quote & Underwriting Pipeline Template

## Overview
Governed workflow for insurance policy issuance, including risk assessment, multi-line bundling, and premium calculation.

Initial Stage: lead_qualification

### Stage: lead_qualification
- **Description**: Verify applicant identity and determine the line of business (Auto, Home, Health).
- **Allowed Agents**: ["IntakeAgent"]
- **Exit Condition**: ctx.has_valid_applicant_profile()
Next Stages:
- asset_verification — if ctx.basic_info_verified()
- clarification — if ctx.missing_pii_data()

### Stage: clarification
- **Description**: Resolve missing data such as VIN numbers, roof age, or prior medical history.
- **Allowed Agents**: ["IntakeAgent", "SupportAgent"]
- **Exit Condition**: ctx.data_gaps_filled()
Next Stages:
- asset_verification — if ctx.data_gaps_filled()
- block — if ctx.applicant_unresponsive()

### Stage: asset_verification
- **Description**: Validate the risk object (e.g., MVR for Auto, CLUE report for Home, or Medical Records for Health).
- **Allowed Agents**: ["RiskDataAgent", "MarketAnalysisAgent"]
- **Exit Condition**: ctx.third_party_data_retrieved()
Next Stages:
- risk_scoring

### Stage: risk_scoring
- **Description**: Actuarial analysis to determine the probability of loss and apply rating factors.
- **Allowed Agents**: ["ActuarialAgent"]
- **Exit Condition**: ctx.risk_tier_assigned()
Next Stages:
- underwriting_review — if ctx.is_standard_risk()
- block — if ctx.outside_risk_appetite()

### Stage: underwriting_review
- **Description**: Formal audit of the quote to ensure compliance with state regulations and company guidelines.
- **Allowed Agents**: ["UnderwritingAgent"]
- **Exit Condition**: ctx.quote_authorized()
Next Stages:
- binding_execution — if ctx.approved()
- risk_scoring — if ctx.premium_adjustment_required()

### Stage: binding_execution
- **Description**: Finalize payment terms, generate policy documents, and "Bind" the coverage.
- **Allowed Agents**: ["TransactionCoordinatorAgent"]
- **Exit Condition**: ctx.payment_verified() and ctx.policy_issued()
Next Stages:
- terminal — if ctx.coverage_active()
- block — if ctx.payment_failed()

### Stage: block
- **Description**: Pipeline halted due to high risk (e.g., DUI, brush fire zone, or pre-existing exclusion).
- **Allowed Agents**: ["SafetyAgent", "ComplianceOfficerAgent"]
Next Stages:
- terminal — if ctx.application_rejected()
- lead_qualification — if ctx.re_application_possible()

### Stage: terminal
- **Description**: Policy bound and active, or application formally declined.
- **Terminal**: true
