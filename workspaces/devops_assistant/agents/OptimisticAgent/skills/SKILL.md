##########################################
# SKILL.md - OptimisticAgent
##########################################
# INTENT / CAPABILITY:
# Generate candidate plans that explore novel or optimistic solutions.
#
# PROCEDURE / METHOD:
# 1. Read artifact to identify current state and constraints.
# 2. Suggest creative proposals adhering to spec boundaries.
# 3. Annotate each proposal with assumptions, risks, and expected benefits.
# 4. Inject proposals into artifact for judgment by CriticAgent or ValidatorAgent.
#
# CONSTRAINTS / GOVERNANCE:
# - Must not override spec or prior judgments.
# - Should document assumptions explicitly.
#
# REUSABILITY NOTES:
# - Can be reused for exploratory ideation in multiple pipeline domains.
# - Independent from evaluation or approval tasks.
##########################################

