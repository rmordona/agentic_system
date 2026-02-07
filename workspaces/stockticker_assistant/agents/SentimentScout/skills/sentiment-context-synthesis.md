---
name: sentiment-context-synthesis
description: Audits social and news narrative for hidden risks or hype.
allowed_tools: [search_ticker_news, analyze_earnings_call]
---
# RUNBOOK: Sentiment Synthesis

## Phase 1: Source Scouring
- Call `search_ticker_news`.
- Identify the "Source Reliability." Ignore low-tier "clickbait" blogs.

## Phase 2: Contextual Audit
- Call `analyze_earnings_call`.
- Compare CEO statements with current news headlines. Look for "Divergence" (e.g., CEO is bullish, but news reports layoffs).

## Phase 3: Narrative Velocity
- Determine if the buzz is organic or "Hype-driven."
