# Travel Orchestration & Booking Pipeline Template
## Overview
This pipeline defines the governed execution flow for a corporate travel booking system, ensuring policy compliance and financial safety.
Goals:
- Prevent unauthorized or out-of-policy financial commitments
- Ensure "Duty of Care" by verifying travel safety and documentation
- Enable multi-option comparison before selection
- Support Human-in-the-Loop (HITL) for final booking confirmation
- Maintain full auditability of travel spend and justifications

Initial Stage: preference_alignment

### Stage: preference_alignment
Description: Intake traveler intent, dates, and destination. Verify baseline constraints.
Allowed Agents: ["TravelLogisticsAgent"]
Exit Condition: `ctx.has_verified_dates_and_intent()`
Next Stages:
- `clarification` — if `ctx.has_ambiguous_dates()`
- `itinerary_discovery` — if `ctx.is_mission_ready()`

### Stage: clarification
Description: Resolve missing data points like passport validity or loyalty IDs.
Allowed Agents: ["TravelLogisticsAgent"]
Exit Condition: `ctx.all_open_questions_resolved()`
Next Stages:
- `itinerary_discovery` — if `ctx.all_open_questions_resolved()`
- `block` — if `ctx.traveler_unresponsive()`

### Stage: itinerary_discovery
Description: Search and aggregate live options for flights, hotels, and transport.
Allowed Agents: ["TravelLogisticsAgent","SearchSpecialistAgent"]
Exit Condition: `len(artifact["proposals"])>=2`
Next Stages:
- `policy_audit`
- `block` — if `ctx.no_viable_options_found()`

### Stage: policy_audit
Description: Evaluate candidate itineraries against Corporate Travel Policy.
Allowed Agents: ["PolicyAuditorAgent"]
Exit Condition: `all_proposals_graded(ctx)`
Next Stages:
- `traveler_selection` — if `ctx.compliant_options_exist()`
- `policy_waiver` — if `ctx.best_options_exceed_policy()`
- `itinerary_discovery` — if `ctx.re_search_required()`

### Stage: policy_waiver
Description: Request manager override for out-of-policy bookings.
Allowed Agents: ["ManagerApprovalAgent"]
Exit Condition: `ctx.hitl_approved==True`
Next Stages:
- `traveler_selection` — if `ctx.approved`
- `block` — if `ctx.denied`

### Stage: traveler_selection
Description: Present curated options to the traveler for final choice.
Allowed Agents: ["TravelLogisticsAgent"]
Exit Condition: `ctx.selection_made==True`
Next Stages:
- `booking_execution` — if `ctx.selection_confirmed()`
- `itinerary_discovery` — if `ctx.selection_rejected()`

### Stage: booking_execution
Description: Perform API calls to book the selected itinerary.
Allowed Agents: ["ProcurementAgent"]
Exit Condition: `ctx.has_confirmation_numbers()`
Next Stages:
- `terminal` — if `ctx.all_bookings_successful()`
- `block` — if `ctx.payment_failed()` or `ctx.price_jump_detected()`

### Stage: block
Description: Pipeline halted due to budget, safety, or communication failure.
Allowed Agents: ["SafetyAgent"]
Exit Condition: `ctx.block_resolved()`
Next Stages:
- `terminal` — if `ctx.mission_aborted()`
- `preference_alignment` — if `ctx.mission_reset_requested()`

### Stage: terminal
Description: Itinerary finalized or mission formally halted.
- Terminal: true
