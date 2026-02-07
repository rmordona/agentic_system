# Financial Intelligence & Execution Pipeline Template

## Overview
This pipeline defines the governed execution flow for a multi-agent stock analysis and execution system.

Goals:
- Prevent high-risk execution during macro-volatility
- Enforce "Check-and-Balance" between Quant and Sentiment data
- Support Human-in-the-Loop (HITL) for trade sizing
- Maintain a Red-Team audit trail for every ticker decision

Initial Stage: macro_context

### Stage: macro_context
Description: Analyze broad market conditions (CPI, Rates, Fed) to determine if trading is safe.
Allowed Agents: ["MacroWatcher"]
Exit Condition: `macro_regime_is_defined(ctx)`
Next Stages:
- ticker_discovery — if `market_open_and_volatility_index(ctx)`
- block — if `extreme_volatility_detected(ctx)`

### Stage: ticker_discovery
Description: Scan for specific ticker signals based on the User's watchlist or sector request.
Allowed Agents: ["QuantAnalyst", "SentimentScout"]
Exit Condition: `active_ticker_context_initialized(ctx)`
Next Stages:
- deep_analysis — if `ticker_signal_detected(ctx)`
- terminal — if `no_trade_setup_found(ctx)`

### Stage: deep_analysis
Description: Parallel deep-dive. Quant checks technicals; Scout audits news and social sentiment.
Allowed Agents: ["QuantAnalyst", "SentimentScout"]
Exit Condition: `analysis_consensus_reached(ctx)`
Next Stages:
- risk_audit — if `is_bullish(ctx) || is_bearish(ctx)`
- block — if `conflicting_data_detected(ctx)` (e.g., Technicals Bullish, News Bearish)

### Stage: risk_audit
Description: Red-team the trade idea. Audit for liquidity, earnings-call proximity, and portfolio VaR.
Allowed Agents: ["RiskGuard"]
Exit Condition: `risk_metrics_within_guardrails(ctx)`
Next Stages:
- hitl_approval — if `trade_size > SYSTEM_LIMIT`
- trade_execution — if `risk_is_accepted(ctx)`
- block — if `risk_threshold_exceeded(ctx)`

### Stage: hitl_approval
Description: Request manual human intervention for high-value or high-risk trades.
Allowed Agents: ["RiskGuard", "TraderAgent"]
Exit Condition: `hitl_action == "APPROVED" || hitl_action == "REJECTED"`
Next Stages:
- trade_execution — if `hitl_action == "APPROVED"`
- terminal — if `hitl_action == "REJECTED"`

### Stage: trade_execution
Description: Atomic execution of the trade through the MCP-connected broker toolkit.
Allowed Agents: ["TraderAgent"]
Exit Condition: `order_status == "FILLED" || order_status == "CANCELLED"`
Next Stages:
- post_trade_audit

### Stage: post_trade_audit
Description: Verify entry price, set stop-losses, and update the `PLAN.md` with exit strategy.
Allowed Agents: ["TraderAgent", "RiskGuard"]
Exit Condition: `state_ledger_updated(ctx)`
Next Stages:
- terminal

### Stage: block
Description: Pipeline halted due to safety, data conflict, or risk violation. Requires manual reset.
Allowed Agents: ["MacroWatcher", "RiskGuard"]
Next Stages:
- terminal — if `incident_report_generated == True`

### Stage: terminal
Description: Task completed. Context cleared for next ticker cycle.
Terminal: true
