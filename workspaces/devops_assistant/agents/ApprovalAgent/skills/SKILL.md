##########################################
# SKILL.md - ApprovalAgent
##########################################
# INTENT / CAPABILITY:
# Evaluate a completed pipeline artifact and grant or deny final approval.
#
# PROCEDURE / METHOD:
# 1. Inspect all prior stage outputs in the artifact.
# 2. Confirm that all exit conditions for non-terminal stages are met.
# 3. Validate HITL approvals where required.
# 4. Check for unresolved issues flagged by SafetyAgent or ValidatorAgent.
# 5. If all checks pass, mark pipeline as approved; else, reject and log reasons.
#
# CONSTRAINTS / GOVERNANCE:
# - Must not bypass HITL-required approvals.
# - Must respect all artifact state; no arbitrary overrides.
#
# REUSABILITY NOTES:
# - Can be reused in any pipeline requiring a final human/system gate.
# - Fully decoupled from proposal generation or ideation stages.
##########################################

