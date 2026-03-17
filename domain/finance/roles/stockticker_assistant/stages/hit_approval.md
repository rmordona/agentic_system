# Stage: hitl_approval

Description:  
Human-in-the-loop approval checkpoint for orders exceeding system limits.

Policy Type: Human Governance  
Priority: 5  
Terminal: False  

Required Agents:
- HumanSupervisor

Entry Predicates:
- order_value is greater than SYSTEM_LIMIT

Exit Predicates:
- hitl_decision is set

Context Inputs:
- order_payload
- risk_metrics

Artifacts Produced:
- hitl_decision

Retry Policy:
- Max Retries: 0

Timeout Seconds: 120

Transition Logic:
- IF hitl_decision is "APPROVED" ALLOW trade_execution
- IF hitl_decision is "REJECTED" ALLOW block
