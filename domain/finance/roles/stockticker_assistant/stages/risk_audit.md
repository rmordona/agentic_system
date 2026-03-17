# Stage: risk_audit

Description:  
Final deterministic safety gate verifying liquidity and Value-at-Risk constraints.

Intent:
- risk_validation
- trade_risk_evaluation
- liquidity_check
- var_verification
- compliance_validation

Policy Type: Risk Governance Gate  
Priority: 4  
Terminal: False  

Required Agents:
- RiskGuard

Entry Predicates:
- quant_signal is set
- sentiment_signal is set

Exit Predicates:
- risk_metrics.var_check is "PASS"
- risk_metrics.liquidity_check is "PASS"

Context Inputs:
- quant_signal
- sentiment_signal
- order_value

Artifacts Produced:
- risk_metrics
- risk_status

Retry Policy:
- Max Retries: 1
- Retry Delay Seconds: 3

Timeout Seconds: 15

Audit:
Level: CRITICAL
Log Inputs: True
Log Outputs: True
Log Transitions: True
Compliance Tags:
- TRADE_RISK_CONTROL
- VAR_GUARDRAIL
- LIQUIDITY_VALIDATION
- PRE_EXECUTION_AUDIT

Transition Logic:
- IF risk_metrics.status is "FAIL" ALLOW block
- IF order_value is greater than SYSTEM_LIMIT ALLOW hitl_approval
- IF risk_metrics.status is "GREEN" ALLOW trade_execution