# Stage: deep_analysis

Description:  
Parallel consensus building combining quantitative signals with market sentiment analysis.

Intent:
- technical_analysis
- signal_generation
- market_analysis

Policy Type: Consensus Formation  
Priority: 3  
Terminal: False  

Required Agents:
- QuantAnalyst
- SentimentScout

Supported Intents:
- stock_analysis

Entry Predicates:
- active_ticker is set

Exit Predicates:
- quant_signal is set
- sentiment_score is set
- signal_confidence is at least 0.60

Context Inputs:
- active_ticker
- ticker_metadata

Artifacts Produced:
- quant_signal
- sentiment_signal
- signal_confidence

Retry Policy:
- Max Retries: 2
- Retry Delay Seconds: 3

Timeout Seconds: 25

Audit:
Level: HIGH
Log Inputs: True
Log Outputs: True
Log Transitions: True
Compliance Tags:
- SIGNAL_GENERATION

Transition Logic:
- IF quant_signal matches sentiment_signal ALLOW risk_audit
- IF quant_signal conflicts with sentiment_signal ALLOW block (Reason: Signal Conflict)