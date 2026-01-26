##########################################
# SKILL.md - SpecInspectorAgent
##########################################
# INTENT / CAPABILITY:
# Inspect specification documents to ensure completeness, consistency, and readability.
#
# PROCEDURE / METHOD:
# 1. Load spec.md from artifact.
# 2. Validate existence and correct formatting.
# 3. Identify missing sections, contradictions, or ambiguities.
# 4. Flag issues in artifact with references to problematic sections.
# 5. Recommend blocking next stages until issues resolved.
#
# CONSTRAINTS / GOVERNANCE:
# - Cannot approve or reject proposals.
# - Must respect artifact state and pipeline governance.
#
# REUSABILITY NOTES:
# - Applicable to any pipeline requiring spec verification.
# - Works before ideation and judgment stages.
##########################################

