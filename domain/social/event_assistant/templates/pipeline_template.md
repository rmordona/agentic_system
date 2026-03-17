# Event Orchestration & Execution Pipeline Template

## Overview

This pipeline defines the governed execution flow for large-scale events, ranging from private celebrations (weddings, birthdays) to professional exhibits and concerts.

Goals:
- Maintain strict alignment between "Vision" and "Budget"
- Manage complex vendor interdependencies (Catering, AV, Venue)
- Enforce safety and permitting compliance for public gatherings
- Support multi-stage Human-in-the-Loop (HITL) for creative approval
- Ensure fail-safe execution through rigorous logistical "Dry Runs"

Initial Stage: vision_alignment

### Stage: vision_alignment
Description: Intake event type, guest count, aesthetic preferences, and budget. Verify baseline feasibility.
Allowed Agents: ["EventStrategistAgent"]
Exit Condition: `ctx.has_verified_scope_and_budget()`
Next Stages:
- clarification — if `ctx.has_vague_creative_intent()`
- venue_discovery — if `ctx.vision_is_executable()`

### Stage: clarification
Description: Resolve ambiguities regarding guest lists, technical requirements for concerts, or theme specifics.
Allowed Agents: ["EventStrategistAgent"]
Exit Condition: `ctx.scope_gaps_resolved()`
Next Stages:
- venue_discovery — if `ctx.scope_gaps_resolved()`
- block — if `ctx.budget_vision_mismatch()`

### Stage: venue_discovery
Description: Source and vet venues based on capacity, acoustics (for concerts), and logistical layout.
Allowed Agents: ["VenueSpecialistAgent", "SearchSpecialistAgent"]
Exit Condition: `len(artifact["venue_options"]) >= 2`
Next Stages:
- vendor_orchestration

### Stage: vendor_orchestration
Description: Sourcing and bidding for catering, AV/Lighting, decor, and entertainment. Aligning vendor timelines.
Allowed Agents: ["LogisticsAgent", "SearchSpecialistAgent"]
Exit Condition: `all_key_service_slots_filled(ctx)`
Next Stages:
- feasibility_audit

### Stage: feasibility_audit
Description: Review the "Run of Show," power requirements for exhibits/concerts, and safety/permitting.
Allowed Agents: ["SafetyAgent", "TechnicalDirectorAgent"]
Exit Condition: `ctx.logistical_plan_validated()`
Next Stages:
- final_judgment — if `ctx.plan_is_safe_and_viable()`
- vendor_orchestration — if `ctx.technical_conflicts_detected()`

### Stage: final_judgment
Description: Final creative and financial sign-off by the client or event owner.
Allowed Agents: ["ClientLiaisonAgent"]
Exit Condition: `ctx.hitl_approved == True`
Next Stages:
- execution_booking — if `ctx.approved_to_book()`
- vision_alignment — if `ctx.major_pivot_requested()`

### Stage: execution_booking
Description: Execute contracts, pay deposits, and lock in the "Master Production Schedule."
Allowed Agents: ["ProcurementAgent"]
Exit Condition: `ctx.all_deposits_confirmed()`
Next Stages:
- terminal — if `ctx.event_is_locked()`
- block — if `ctx.vendor_availability_lost()`

### Stage: block
Description: Pipeline halted due to permit denial, budget breach, or critical vendor cancellation.
Allowed Agents: ["SafetyAgent", "EventStrategistAgent"]
Next Stages:
- terminal — if `ctx.event_cancelled()`
- vision_alignment — if `ctx.replan_triggered()`

### Stage: terminal
Description: Event successfully booked and scheduled, or formally cancelled.
Terminal: true

---
