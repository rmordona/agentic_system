# Stage: macro_context

Description:  
Primary entry gate. Evaluates macroeconomic conditions and systemic risk before enabling downstream trading activity.

Intent:
- initialize_session
- risk_screening
- macro_regime_detection

Policy Type: Initializer / Market Safety Gate  
Priority: 1  
Terminal: False  

Required Agents:
- MacroWatcher

Supported Intents:
- portfolio_risk
- trade_execution
- stock_analysis

Entry Predicates:
- None

Exit Predicates:
- macro_analysis.regime is set
- macro_analysis.risk_index is between [1,10]

Context Inputs:
- vix
- breaking_news_risk
- macro_analysis

Artifacts Produced:
- macro_analysis

Retry Policy:
- Max Retries: 1
- Retry Delay Seconds: 5

Timeout Seconds: 15

Audit:
Level: HIGH
Log Inputs: True
Log Outputs: True
Log Transitions: True
Compliance Tags:
- MARKET_RISK_CHECK
- MACRO_GUARDRAIL

Transition Logic:
- IF vix is greater than VIX_MAX ALLOW block (Reason: Excessive Volatility)
- IF breaking_news_risk is True ALLOW block (Reason: Event Risk)
- IF macro_analysis.trade_permission is True ALLOW ticker_discovery
- IF macro_analysis.risk_index is greater than 8 ALLOW block (Reason: Macro Regime Risk)