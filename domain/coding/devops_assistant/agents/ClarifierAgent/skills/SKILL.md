##########################################
# SKILL.md - ClarifierAgent
##########################################
# INTENT / CAPABILITY:
# Resolve ambiguities or contradictions in artifact proposals.
#
# PROCEDURE / METHOD:
# 1. Inspect artifact for unclear or conflicting proposals.
# 2. Generate questions or HITL prompts to clarify ambiguities.
# 3. Update artifact with clarified information or flags for further review.
# 4. Route clarified proposals back to ideation or judgment stages.
#
# CONSTRAINTS / GOVERNANCE:
# - Must not make final approval decisions.
# - Must respect prior agent evaluations and artifact integrity.
#
# REUSABILITY NOTES:
# - Reusable in pipelines with HITL escalation or ambiguity resolution.
# - Independent of proposal generation mechanisms.
##########################################

