# Stage: trade_execution

Description:  
Atomic order submission stage enforcing slippage limits and signal freshness.

Intent:
- trade_execution
- order_submission

Policy Type: Atomic Execution  
Priority: 6  
Terminal: False  

Required Agents:
- ExecutionAgent

Supported Intents:
- trade_execution

Entry Predicates:
- risk_status is "GREEN" OR hitl_decision is "APPROVED"
- ticker matches active_ticker
- signal_age is less than MAX_SIGNAL_AGE_SECONDS
- price_slippage is less than 0.02

Exit Predicates:
- execution_status is set

Context Inputs:
- order_payload
- signal_age
- price_slippage

Artifacts Produced:
- execution_status
- trade_receipt

Retry Policy:
- Max Retries: 3
- Retry Delay Seconds: 2

Timeout Seconds: 10

Audit:
Level: CRITICAL
Log Inputs: True
Log Outputs: True
Log Transitions: True
Compliance Tags:
- TRADE_EXECUTION
- FINANCIAL_TRANSACTION
- AUDIT_REQUIRED

Transition Logic:
- IF execution_status is "FILLED" ALLOW post_trade_audit
- IF execution_status is "REJECTED" ALLOW block
- IF signal_age is at least MAX_SIGNAL_AGE_SECONDS ALLOW macro_context (Reason: Stale Signal)