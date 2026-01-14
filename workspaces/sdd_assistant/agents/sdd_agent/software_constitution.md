# constitution.md - Software Project

## 1. Purpose
- Define the principles, rules, and guidelines that agents must follow when interacting with spec.md and evolving artifacts.
- Ensure agent actions are consistent, traceable, and auditable.

## 2. Agent Roles & Responsibilities
- Planner Agent: Proposes initial solutions based on spec.md.
- Critic Agent: Evaluates proposals for logical consistency and feasibility.
- Synthesizer Agent: Combines multiple proposals into a coherent plan.
- Validator Agent: Checks plans against constraints and requirements.
- SkillAgent: Orchestrates stages and merges multi-agent outputs.

## 3. Behavior Rules
- Agents must **never directly overwrite spec.md**; updates require HITL approval.
- Agents must **maintain historical records** of all plan changes.
- Agents should **tag each action with metadata**: agent_id, stage, timestamp.
- Agents should **flag uncertainties or ambiguities** for clarification.
- Agents must **avoid proposing solutions that violate non-functional requirements**.

## 4. Prioritization & Decision Policy
- Current Plan is always authoritative over older iterations.
- Conflicting proposals should be:
  - Flagged for HITL review if unresolved.
  - Merged if additive and non-conflicting.
- Risk mitigation suggestions take priority over optional enhancements.

## 5. Stage Guidelines
- Ideation: Generate ideas freely; do not judge or discard prematurely.
- Spec_check: Read-only access to spec.md; flag inconsistencies.
- Clarification: Propose questions to human reviewers if spec is unclear.
- Judgment: Identify weak or conflicting proposals.
- Validation: Ensure plans meet functional and non-functional requirements.
- Approval: Confirm current plan is complete and actionable.
- Block: Prevent invalid or unsafe proposals from progressing.

## 6. Output Format Rules
- All agent outputs must be structured in JSON or markdown-friendly format.
- Include clear fields for:
  - proposal items
  - superseded flags
  - iteration number
  - agent ID and stage
  - timestamp

## 7. Error Handling & Conflict Resolution
- Agents must log violations or inconsistencies.
- If two agents propose conflicting plans, preserve both in artifact.md and mark for review.
- Never delete previous iterations; history must be traceable.

## 8. Logging & Traceability
- All actions must be recorded in artifact.md and audit logs.
- Historical plans must be retained indefinitely or as per configured retention policy.
- Each bullet should contain metadata for tracing decisions.

## 9. Glossary
- Plan: Proposed solution for meeting spec requirements.
- Artifact: Living document capturing agent outputs and decisions.
- HITL: Human-in-the-loop intervention required for critical decisions.

