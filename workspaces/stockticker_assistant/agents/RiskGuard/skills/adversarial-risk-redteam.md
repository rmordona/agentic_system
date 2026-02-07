---
name: adversarial-risk-redteam
description: Stress-tests the trade plan against Black Swan events.
allowed_tools: [calculate_var]
---
# RUNBOOK: Risk Red-Team

## Phase 1: Exposure Audit
- Read the outputs from QuantAnalyst and SentimentScout.
- Call `calculate_var` based on the proposed ticker.

## Phase 2: The "What-If" Analysis
- Audit for "Earnings Proximity." If earnings are within 48 hours, the trade is `REJECTED`.
- Check `liquidity_rating`. If the spread is > 1%, the trade is `REJECTED`.

## Phase 3: Final Handoff
- Formulate the `veto_reasons` if any check fails.
