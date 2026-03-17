# Stage: ticker_discovery

Description:  
Scans market data to identify specific tickers aligned with approved macro themes.

Intent:
- ticker_lookup
- ticker_validation
- ticker_resolution

Policy Type: Context Acquisition  
Priority: 2  
Terminal: False  

Required Agents:
- QuantAnalyst
- SentimentScout

Supported Intents:
- price_lookup
- historical_data
- stock_analysis

Entry Predicates:
- macro_analysis.trade_permission is True
- market_status is "OPEN"

Exit Predicates:
- active_ticker is set
- ticker_metadata contains ["sector", "volatility"]

Context Inputs:
- macro_analysis
- market_status

Artifacts Produced:
- active_ticker
- ticker_metadata

Retry Policy:
- Max Retries: 2
- Retry Delay Seconds: 3

Timeout Seconds: 20

Audit:
Level: MEDIUM
Log Inputs: True
Log Outputs: True
Log Transitions: True
Compliance Tags:
- ASSET_DISCOVERY

Transition Logic:
- IF active_ticker is set ALLOW deep_analysis