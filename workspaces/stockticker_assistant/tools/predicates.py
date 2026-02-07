from runtime.policy_registry import Predicates, StageEvalContext

class Policies:
################################################################################
# Policy Predicate Implementation
################################################################################

    @Predicates.policy()
    def artifact_is_valid(ctx: StageEvalContext) -> bool:
        """
        Returns True if the artifact is valid:
        - No validation errors
        - No spec conflicts
        - No open tasks
        - All recent tools succeeded
        """
        artifact_ok = (
            len(ctx.artifact.get("validation_errors", [])) == 0
            and len(ctx.artifact.get("spec_conflicts", [])) == 0
            and len(ctx.artifact.get("open_tasks", [])) == 0
        )

        tools_ok = all(t.get("success", False) for t in ctx.tools)

        return artifact_ok and tools_ok

    @Predicates.policy()
    def clarifications_resolved(ctx: StageEvalContext) -> bool:
        return not any(
            t.tool_name == "request_clarification" and t.success is False
            for t in ctx.tools
        )

    @Predicates.policy()
    def hitl_approved(ctx: StageEvalContext) -> bool:
        return ctx.hitl_flags.get("approved") is True

    @Predicates.policy()
    def human_approved(ctx: StageEvalContext) -> bool:
        return ctx.hitl_flags.get("approved") is True

    @Predicates.policy()
    def all_proposals_reviewed(ctx: StageEvalContext) -> bool:
        proposals = ctx.artifact.get("proposals", [])
        return all(p.get("reviewed") is True for p in proposals)

    @Predicates.policy()
    def accepted_proposals_exist(ctx: StageEvalContext) -> bool:
        return any(
            p.get("status") == "accepted"
            for p in ctx.artifact.get("proposals", [])
        )

    @Predicates.policy()
    def all_proposals_invalid(ctx: StageEvalContext) -> bool:
        proposals = ctx.artifact.get("proposals", [])
        return proposals and all(
            p.get("status") in {"rejected", "invalid"}
            for p in proposals
        )

    @Predicates.policy()
    def artifact_requires_new_ideas(ctx: StageEvalContext) -> bool:
        return (
            ctx.artifact.get("proposals")
            and not accepted_proposals_exist(ctx)
            and ctx.artifact.get("iteration_count", 0) < ctx.artifact.get("max_iterations", 3)
        )

    @Predicates.policy()
    def critical_issues_detected(ctx: StageEvalContext) -> bool:
        return any(
            issue.get("severity") == "critical"
            for issue in ctx.artifact.get("issues", [])
        )

    @Predicates.policy()
    def proposal_conflicts_with_spec(ctx: StageEvalContext) -> bool:
        return any(
            p.get("status") == "accepted" and p.get("spec_conflict") is True
            for p in ctx.artifact.get("proposals", [])
        )

    @Predicates.policy()
    def artifact_has_spec_gaps(ctx: StageEvalContext) -> bool:
        return bool(ctx.artifact.get("spec_gaps"))

    @Predicates.policy()
    def clarifications_resolved(ctx: StageEvalContext) -> bool:
        return not any(
            t.tool_name == "request_clarification" and not t.success
            for t in ctx.tools
        )

    @Predicates.policy()
    def clarification_failed(ctx: StageEvalContext) -> bool:
        return any(
            t.tool_name == "request_clarification"
            and t.success is False
            and t.output.get("status") == "FAILED"
            for t in ctx.tools
        )

    @Predicates.policy()
    def macro_regime_is_defined(ctx: StageEvalContext) -> bool:
        """Checks if MacroWatcher has categorized the market volatility."""
        data = ctx.get("macro_analysis", {})
        # Must have a recognized regime and a risk index to proceed
        return bool(data.get("regime") and "risk_index" in data)

    @Predicates.policy()
    def active_ticker_context_initialized(ctx: StageEvalContext) -> bool:
        """Ensures a specific ticker is targeted and basic stats are loaded."""
        ticker = ctx.get("active_ticker")
        stats = ctx.get("ticker_stats", {})
        return bool(ticker and stats.get("current_price"))

    @Predicates.policy()
    def analysis_consensus_reached(ctx: StageEvalContext) -> bool:
        """
        Verifies that both QuantAnalyst and SentimentScout have 
        submitted their respective YAML-validated reports.
        """
        quant_done = "signals" in ctx.get("quant_report", {})
        sentiment_done = "sentiment_score" in ctx.get("sentiment_report", {})
        return quant_done and sentiment_done

    @Predicates.policy()
    def risk_metrics_within_guardrails(ctx: StageEvalContext) -> bool:
        """Checks if RiskGuard has completed the audit and rendered a verdict."""
        audit = ctx.get("risk_audit", {})
        # The presence of a 'risk_verdict' (APPROVED/REJECTED) satisfies the exit condition
        return audit.get("risk_verdict") in ["APPROVED", "REJECTED"]

    @Predicates.policy()
    def hitl_approved_or_rejected(ctx: StageEvalContext) -> bool:
        """Exit condition for the HITL (Human-in-the-Loop) stage."""
        action = ctx.get("hitl_action")
        return action in ["APPROVED", "REJECTED"]

    @Predicates.policy()
    def order_is_terminal(ctx: StageEvalContext) -> bool:
        """Checks if the TraderAgent's order has reached a final state."""
        status = ctx.get("order_status")
        return status in ["FILLED", "CANCELLED", "FAILED"]

    @Predicates.policy()
    def state_ledger_updated(ctx: StageEvalContext) -> bool:
        """Ensures the post-trade audit has written back to the artifact/ledger."""
        return ctx.get("ledger_entry_confirmed", False)

    @Predicates.policy()
    def route_after_risk(state):
        if risk_metrics_within_guardrails(state):
            if state["risk_audit"]["risk_verdict"] == "APPROVED":
                return "trade_execution"
            return "terminal" # Rejected trade
        return "risk_audit" # Stay in node if metrics aren't defined yet