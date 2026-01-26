# Realty Acquisition & Due Diligence Pipeline Template

## Overview
This pipeline defines the governed execution flow for real estate asset identification, valuation, and acquisition.

Initial Stage: asset_alignment

### Stage: asset_alignment
- **Description**: Intake property requirements (location, asset type, cap rate) and verify buyer's proof of funds.
- **Allowed Agents**: ["RealtyStrategyAgent"]
- **Exit Condition**: ctx.has_verified_buy_box_and_funds()
Next Stages:
- clarification — if ctx.has_ambiguous_criteria()
- asset_sourcing — if ctx.target_criteria_defined()

### Stage: clarification
- **Description**: Resolve ambiguities in the "Buy Box" or missing financial documentation.
- **Allowed Agents**: ["RealtyStrategyAgent"]
- **Exit Condition**: ctx.alignment_gaps_resolved()
Next Stages:
- asset_sourcing — if ctx.alignment_gaps_resolved()
- block — if ctx.buyer_intent_unclear()

### Stage: asset_sourcing
- **Description**: Strategic channel activation. Broker outreach and direct-to-owner networking.
- **Allowed Agents**: ["MarketAnalysisAgent", "SearchSpecialistAgent"]
- **Exit Condition**: ctx.sourcing_channels_active()
Next Stages:
- property_discovery

### Stage: property_discovery
- **Description**: Tactical scanning of MLS, off-market databases, and internal lead feeds to populate candidates.
- **Allowed Agents**: ["SearchSpecialistAgent"]
- **Exit Condition**: len(artifact["proposals"]) >= 1
Next Stages:
- financial_underwriting — if ctx.has_raw_leads()
- asset_sourcing — if ctx.no_market_matches_found()

### Stage: financial_underwriting
- **Description**: Deep-dive financial modeling. Calculation of NOI, IRR, and Cash-on-Cash returns.
- **Allowed Agents**: ["UnderwritingAgent"]
- **Exit Condition**: ctx.model_verification_complete()
Next Stages:
- site_inspection — if ctx.meets_yield_threshold()
- asset_sourcing — if ctx.financials_rejected()

### Stage: site_inspection
- **Description**: Physical walkthrough and structural assessment of the asset.
- **Allowed Agents**: ["InspectorAgent"]
- **Exit Condition**: ctx.inspection_report_filed()
Next Stages:
- investment_committee — if ctx.no_critical_defects_found()
- block — if ctx.structural_failure_detected()
- financial_underwriting — if ctx.renegotiation_required_due_to_repairs()

### Stage: investment_committee
- **Description**: Formal review of the deal book for final internal Go/No-Go decision.
- **Allowed Agents**: ["InvestmentCommitteeAgent"]
- **Exit Condition**: ctx.hitl_approval_granted()
Next Stages:
- due_diligence — if ctx.approved_for_loi()
- block — if ctx.deal_vetoed()

### Stage: due_diligence
- **Description**: Legal and environmental audit. Title search and zoning verification.
- **Allowed Agents**: ["DueDiligenceAgent", "LegalCounselAgent"]
- **Exit Condition**: ctx.title_clearance_received()
Next Stages:
- offer_execution — if ctx.diligence_passed()
- block — if ctx.legal_encumbrance_found()

### Stage: offer_execution
- **Description**: Draft and submit LOIs or Purchase Agreements. Manage escrow opening.
- **Allowed Agents**: ["TransactionCoordinatorAgent"]
- **Exit Condition**: ctx.has_signed_contract()
Next Stages:
- terminal — if ctx.contract_fully_executed()
- block — if ctx.offer_rejected() or ctx.legal_deadlock()

### Stage: block
- **Description**: Pipeline halted due to title defects, structural issues, or financial hurdles.
- **Allowed Agents**: ["SafetyAgent", "LegalCounselAgent"]
Next Stages:
- terminal — if ctx.deal_aborted()
- asset_alignment — if ctx.restart_with_new_parameters()

### Stage: terminal
- **Description**: Property acquired or acquisition attempt formally terminated.
- **Terminal**: true