# Stage: post_trade_audit

Description:  
Post-execution compliance and reporting stage responsible for final audit logging.

Policy Type: Compliance Audit  
Priority: 7  
Terminal: True  

Required Agents:
- ComplianceAuditor

Entry Predicates:
- execution_status is "FILLED"

Exit Predicates:
- trade_record is persisted

Context Inputs:
- trade_receipt
- risk_metrics

Artifacts Produced:
- audit_report
- trade_record

Retry Policy:
- Max Retries: 2
- Retry Delay Seconds: 5

Timeout Seconds: 20

Transition Logic:
- ALWAYS ALLOW terminal
