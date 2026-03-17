---
name: tactical-trade-execution
description: Executes the trade with minimal slippage.
allowed_tools: [execute_trade]
---
# RUNBOOK: Tactical Execution

## Phase 1: Pre-Flight Check
- Verify that `risk_verdict` in the context is `APPROVED`.
- **Constraint:** Do NOT execute if `order_id` already exists for this ticker (prevent double-fills).

## Phase 2: Execution
- Call `execute_trade` using the `max_position_size` and `price_targets` provided by previous nodes.

## Phase 3: Confirmation
- Log the `average_price` and `total_cost` into the state ledger.
