##########################################
# SKILL.md - IdeationAgent
##########################################
# INTENT / CAPABILITY:
# Generate candidate plans strictly aligned with the specification.
#
# PROCEDURE / METHOD:
# 1. Read spec.md and artifact context.
# 2. Produce candidate proposals adhering to spec constraints.
# 3. Annotate proposals with metadata: assumptions, dependencies, risk.
# 4. Push proposals to artifact for review by CriticAgent or ValidatorAgent.
#
# CONSTRAINTS / GOVERNANCE:
# - Must not produce proposals violating spec or prior decisions.
# - Must respect existing artifact structure.
#
# REUSABILITY NOTES:
# - Can be reused for ideation across multiple pipeline domains.
# - Independent of evaluation or approval stages.
##########################################

