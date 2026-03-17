# Financial Execution Governance Policy (GEP)

Version: 1.1
Policy Owner: Institutional Risk & Compliance
Execution Model: Deterministic State Machine

---

## Global Constraints
These constants define the non-negotiable safety boundaries for the system.

- VIX_MAX: 35
- SYSTEM_LIMIT: 50000
- MAX_EXECUTION_RETRIES: 3
- MAX_SIGNAL_AGE_SECONDS: 30

---

## 1. Stage: macro_context
Description: Primary entry gate. Analyzes global macro factors to ensure the environment supports risk-taking.
Policy Type: Initializer / Market Safety Gate

Required Agents: ["MacroWatcher"]

Exit Predicates:
- macro_analysis.regime is set
- macro_analysis.risk_index is between [1, 10]

Transition Logic:
- IF vix is greater than VIX_MAX ALLOW block (Reason: Excessive Volatility)
- IF breaking_news_risk is True ALLOW block (Reason: Event Risk)
- IF macro_analysis.trade_permission is True ALLOW ticker_discovery
- IF macro_analysis.risk_index is greater than 8 ALLOW block (Reason: Macro Regime Risk)

---

## 2. Stage: ticker_discovery
Description: Scans market data to identify specific tickers that align with approved macro themes.
Policy Type: Context Acquisition

Required Agents: ["QuantAnalyst", "SentimentScout"]

Entry Predicates:
- macro_analysis.trade_permission is True
- market_status is "OPEN"

Exit Predicates:
- active_ticker is set
- ticker_metadata contains ["sector", "volatility"]

---

## 3. Stage: deep_analysis
Description: Parallel consensus building. Forces technical and narrative data to reach a unified conclusion.
Policy Type: Consensus Formation

Required Agents: ["QuantAnalyst", "SentimentScout"]

Exit Predicates:
- quant_signal is set
- sentiment_score is set
- signal_confidence is at least 0.60

Transition Logic:
- IF quant_signal matches sentiment_signal ALLOW risk_audit
- IF quant_signal conflicts with sentiment_signal ALLOW block (Reason: Signal Conflict)

---

## 4. Stage: risk_audit
Description: Final deterministic safety gate. Audits for liquidity and Value-at-Risk compliance.
Policy Type: Risk Governance Gate

Required Agents: ["RiskGuard"]

Exit Predicates:
- risk_metrics.var_check is "PASS"
- risk_metrics.liquidity_check is "PASS"

Transition Logic:
- IF risk_metrics.status is "FAIL" ALLOW block
- IF order_value is greater than SYSTEM_LIMIT ALLOW hitl_approval
- IF risk_metrics.status is "GREEN" ALLOW trade_execution

---

## 5. Stage: trade_execution
Description: Atomic fulfillment. Submission of order payload while enforcing price/time slippage limits.
Policy Type: Atomic Execution

Entry Predicates:
- risk_status is "GREEN" or hitl_decision is "APPROVED"
- ticker matches active_ticker
- signal_age is less than MAX_SIGNAL_AGE_SECONDS
- price_slippage is less than 0.02

Transition Logic:
- IF execution_status is "FILLED" ALLOW post_trade_audit
- IF execution_status is "REJECTED" ALLOW block
- IF signal_age is at least MAX_SIGNAL_AGE_SECONDS ALLOW macro_context (Reason: Stale Data)

---

## 8. Stage: block
Description: Emergency safety halt. Stops processing when a policy violation occurs.
Policy Type: Safety Shutdown

Transition Logic:
- ALWAYS ALLOW terminal
