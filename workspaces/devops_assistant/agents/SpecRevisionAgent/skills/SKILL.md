##########################################
# SKILL.md - SpecRevisionAgent
##########################################
# INTENT / CAPABILITY:
# Propose updates or revisions to specification documents.
#
# PROCEDURE / METHOD:
# 1. Review flagged issues in artifact from SpecInspectorAgent or ValidatorAgent.
# 2. Draft proposed changes to spec.md in a controlled, versioned manner.
# 3. Annotate revision with rationale, dependencies, and risks.
# 4. Submit revision for HITL approval; do not apply autonomously.
#
# CONSTRAINTS / GOVERNANCE:
# - Must never apply changes without explicit HITL approval.
# - Must preserve auditability of prior spec versions.
#
# REUSABILITY NOTES:
# - Can be reused across pipelines requiring spec evolution.
# - Works independently from ideation or approval stages.
##########################################

