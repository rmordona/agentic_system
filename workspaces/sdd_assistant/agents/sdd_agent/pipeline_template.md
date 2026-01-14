###########################################################################
# Specification-Driven Development (SDD) Pipeline Template
###########################################################################

# 1. spec.md - Requirements / Goals
Purpose: Define the authoritative requirements that the agents will work from. 
Agents read this but do not directly modify it; human-in-the-loop approval is required for updates.

## Sections
- Project / Event Overview
- Objectives & Goals
- Functional Requirements
- Non-Functional Requirements
- User Stories / Use Cases
- System Architecture / Logistics
- Interfaces / Dependencies
- Data Models / Resources
- Constraints & Assumptions
- Acceptance Criteria
- Risks & Mitigations
- Glossary

## Example (Generic)
- Overview: Organize a virtual conference for 500+ attendees
- Objectives: Ensure schedule accuracy, maximize attendee satisfaction, stay within budget
- Functional: Online registration, QR check-in, session notifications
- Non-Functional: System must handle 500 concurrent users, accessible to all attendees
- Acceptance Criteria: 100% registration confirmation sent, no scheduling conflicts
- Glossary: Attendee = registered participant, Session = talk/workshop

---

# 2. constitution.md - Rules & Agent Behavior
Purpose: Define **how agents must behave** across all stages, including constraints, priorities, and output rules. This governs agent interaction with spec.md and artifact.md.

## Sections
- Purpose
- Agent Roles & Responsibilities
- Behavior Rules
- Prioritization & Decision Policy
- Stage Guidelines (Ideation, Spec_Check, Clarification, Judgment, Validation, Approval, Block)
- Output Format Rules (JSON / Markdown)
- Error Handling & Conflict Resolution
- Logging & Traceability
- Domain-Specific Placeholders
- Glossary / Definitions

## Example Rules
- Agents never overwrite spec.md directly
- Current plan always supersedes historical plans
- Metadata must include: agent_id, stage, timestamp, superseded
- Conflicting proposals are flagged for HITL review
- Historical plans are preserved in artifact.md

---

# 3. artifact.md / plan.md - Evolving Outputs
Purpose: Living document capturing all **agent-generated plans, proposals, violations, and resolutions**. Updated each stage and iteration.

## Sections
### Current Plan
- List actionable plan items, with metadata (agent_id, stage, timestamp, superseded=false)

### History of Plans
- Iteration 1
  - Superseded plan items (superseded=true)
- Iteration 2
  - Superseded plan items (superseded=true)
- Iteration N
  - Superseded plan items (superseded=true)

### Violations / Warnings (Optional)
- Policy or constraint violations detected by agents
- Example: Node 14 deprecated, budget exceeded, schedule conflict

### Resolved Proposals (Optional)
- List of proposals that were reviewed and approved (HITL or agent resolution)

---

# 4. Stage & Agent Interaction
Purpose: Show how stages map to agent actions and document updates.

| Stage          | Allowed Agents          | Artifact Updates                  | spec.md | constitution.md |
|----------------|-----------------------|---------------------------------|---------|----------------|
| Ideation       | Planner, SkillAgent    | Proposals in Current Plan        | Read    | Read           |
| Spec_Check     | Critic                 | Flags inconsistencies            | Read    | Read           |
| Clarification  | Planner, Critic        | Questions / Missing Info         | Read    | Read           |
| Judgment       | Critic, Synthesizer    | Evaluate, mark weak/conflict     | Read    | Read           |
| Validation     | Validator, SkillAgent  | Confirm feasibility, add violations | Read  | Read           |
| Approval       | SkillAgent             | Mark plan ready for execution    | Read    | Read           |
| Block          | Critic, Validator      | Prevent invalid proposals        | Read    | Read           |

**Notes:**
- Artifact.md / plan.md grows with iterations; new proposals merge with current plan and old proposals are superseded.
- Agents follow constitution.md for behavior rules, output formatting, and conflict resolution.
- Human-in-the-loop (HITL) interventions are triggered if agents propose spec changes or critical conflicts.

---

# 5. Multi-Agent Proposal Flow (Illustrative)

```text
[Spec.md] --> read-only for agents
[Constitution.md] --> guides agent behavior

Stage: Ideation
  Agent A proposes plan items --> Current Plan in artifact.md
  Agent B proposes concurrently --> Merged into Current Plan

Stage: Judgment
  Critic Agent evaluates, marks weak items --> updates superseded flags

Stage: Validation
  Validator Agent checks feasibility, flags violations --> updates artifact.md

Stage: Approval
  SkillAgent finalizes Current Plan --> marked ready for execution

HITL (if necessary)
  Humans review proposed spec changes or blocked items

