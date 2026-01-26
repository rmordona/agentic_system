##########################################
# SKILL.md - SynthesizerAgent
##########################################
# INTENT / CAPABILITY:
# Combine multiple proposals or artifacts into a coherent summary.
#
# PROCEDURE / METHOD:
# 1. Retrieve candidate proposals from artifact.
# 2. Merge proposals while preserving conflicts and metadata.
# 3. Annotate synthesized artifact with highlights, conflicts, and dependencies.
# 4. Prepare consolidated artifact for downstream stages (ValidatorAgent, ApprovalAgent).
#
# CONSTRAINTS / GOVERNANCE:
# - Cannot modify original proposals; only synthesize.
# - Must retain audit trail of combined proposals.
#
# REUSABILITY NOTES:
# - Reusable wherever multiple artifacts need consolidation.
# - Can be reused in judgment, validation, or reporting pipelines.
##########################################

