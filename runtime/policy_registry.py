import ast
from typing import Any, Callable, Dict
from dataclasses import dataclass, field

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger( component="system" )


@dataclass(frozen=True)
class StageEvalContext:
    artifact: dict
    data: dict
    tools: list[ToolEnvelope]
    hitl_flags: dict
    stage: str

class PolicyRegistry:

    VARIABLES = {
        "hitl_approved": False,
        "human_abort_confirmed": False,
    }

    def __init__(self):
        self._predicates: dict[str, Callable[[StageEvalContext], bool]] = {}
        self.initialize()

    def initialize(self):
        self.register("artifact_is_valid", artifact_is_valid)
        self.register("human_approved", human_approved)
        self.register("all_proposals_reviewed", all_proposals_reviewed)
        self.register("accepted_proposals_exist", accepted_proposals_exist)
        self.register("all_proposals_invalid", all_proposals_invalid)
        self.register("artifact_requires_new_ideas", artifact_requires_new_ideas)
        self.register("critical_issues_detected", critical_issues_detected)
        self.register("proposal_conflicts_with_spec", proposal_conflicts_with_spec)
        self.register("artifact_has_spec_gaps", artifact_has_spec_gaps)
        self.register("clarifications_resolved", clarifications_resolved)
        self.register("clarification_failed", clarification_failed)

        self.evaluator = ExitConditionEvaluator(self._predicates, self.VARIABLES)
    
    def register(self, name: str, fn: Callable):
        self._predicates[name] = fn

    def compile(self, expr: str) -> ast.Expression:
        return self.evaluator.compile(expr)

    def evaluate(
        self,
        compiled_expr: ast.Expression,
        artifact: dict,
        state_ctx: dict | None = None,
    ) -> bool:

        # Compose the StageEvalContext
        # Note that:
        #    data and tools are the data and tools context from core_engine.py build_run_state_context
        ctx_obj = StageEvalContext(
            artifact=artifact,
            data=state_ctx.get("data", {}),
            tools=state_ctx.get("recent_tools", []),
            hitl_flags=state_ctx.get("workflow_metadata", {}).get("hitl_flags", {}),
            stage=state_ctx.get("stage", "unknown")
        )

        return self.evaluator.evaluate(compiled_expr, ctx_obj)

################################################################################
# Policy Predicate Implementation
################################################################################
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



def clarifications_resolved(ctx: StageEvalContext) -> bool:
    return not any(
        t.tool_name == "request_clarification" and t.success is False
        for t in ctx.tools
    )

def hitl_approved(ctx: StageEvalContext) -> bool:
    return ctx.hitl_flags.get("approved") is True

def human_approved(ctx: StageEvalContext) -> bool:
    return ctx.hitl_flags.get("approved") is True

def all_proposals_reviewed(ctx: StageEvalContext) -> bool:
    proposals = ctx.artifact.get("proposals", [])
    return all(p.get("reviewed") is True for p in proposals)

def accepted_proposals_exist(ctx: StageEvalContext) -> bool:
    return any(
        p.get("status") == "accepted"
        for p in ctx.artifact.get("proposals", [])
    )

def all_proposals_invalid(ctx: StageEvalContext) -> bool:
    proposals = ctx.artifact.get("proposals", [])
    return proposals and all(
        p.get("status") in {"rejected", "invalid"}
        for p in proposals
    )

def artifact_requires_new_ideas(ctx: StageEvalContext) -> bool:
    return (
        ctx.artifact.get("proposals")
        and not accepted_proposals_exist(ctx)
        and ctx.artifact.get("iteration_count", 0) < ctx.artifact.get("max_iterations", 3)
    )

def critical_issues_detected(ctx: StageEvalContext) -> bool:
    return any(
        issue.get("severity") == "critical"
        for issue in ctx.artifact.get("issues", [])
    )

def proposal_conflicts_with_spec(ctx: StageEvalContext) -> bool:
    return any(
        p.get("status") == "accepted" and p.get("spec_conflict") is True
        for p in ctx.artifact.get("proposals", [])
    )

def artifact_has_spec_gaps(ctx: StageEvalContext) -> bool:
    return bool(ctx.artifact.get("spec_gaps"))

def clarifications_resolved(ctx: StageEvalContext) -> bool:
    return not any(
        t.tool_name == "request_clarification" and not t.success
        for t in ctx.tools
    )

def clarification_failed(ctx: StageEvalContext) -> bool:
    return any(
        t.tool_name == "request_clarification"
        and t.success is False
        and t.output.get("status") == "FAILED"
        for t in ctx.tools
    )



class ExitConditionError(Exception):
    pass

class ExitConditionEvaluator:
    """
    Safely evaluates declarative exit-condition expressions
    using AST validation and a strict symbol registry.
    """

    # -----------------------------
    # Allowed AST Nodes
    # -----------------------------
    ALLOWED_NODES = {
        ast.Expression,
        ast.BoolOp,
        ast.Compare,
        ast.Call,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.Subscript,
        ast.Index,
        ast.BinOp,
        ast.And,
        ast.Or,
        ast.Eq,
        ast.NotEq,
        ast.Gt,
        ast.GtE,
        ast.Lt,
        ast.LtE,
    }

    ALLOWED_BUILTINS = {
        "len": len, "any": any, "all": all, "sum": sum, "min": min, "max": max
    }

    # -----------------------------
    # Construction
    # -----------------------------
    def __init__(
        self,
        function_registry: Dict[str, Callable],
        variable_registry: Dict[str, Any] | None = None,
    ):
        self.function_registry = function_registry
        self.variable_registry = variable_registry or {}

    # -----------------------------
    # Public API
    # -----------------------------
    def compile(self, expression: str) -> ast.Expression:
        """
        Compile and validate an exit condition expression.
        Call this ONCE during pipeline load.
        """
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            raise ExitConditionError(f"Invalid exit condition syntax: {e}")

        self._validate_ast(tree)
        self._validate_symbols(tree)

        return tree

    def evaluate(
        self,
        compiled_expr: ast.Expression,
        ctx_obj: StageEvalContext,
    ) -> bool:
        """
        Evaluate a previously compiled exit condition.
        """

        logger.info(f"Context Object: {ctx_obj}")
        context = {
            "__builtins__": {},
            "ctx" : ctx_obj,
            "artifact" : ctx_obj.artifact,
            **self.ALLOWED_BUILTINS,
            **self.function_registry,
            **self.variable_registry,
        }

        # try:
        return bool(eval(compile(compiled_expr, "<exit_condition>", "eval"), context))
        #except Exception as e:
        #     raise ExitConditionError(f"Exit condition evaluation failed: {e}")

    # -----------------------------
    # Validation
    # -----------------------------
    def _validate_ast(self, tree: ast.AST):
        for node in ast.walk(tree):
            if not isinstance(node, tuple(self.ALLOWED_NODES)):
                raise ExitConditionError(
                    f"Disallowed AST node: {type(node).__name__}"
                )

            # No attribute access (artifact.foo)
            if isinstance(node, ast.Attribute):
                raise ExitConditionError("Attribute access is not allowed")

            # No arbitrary calls
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name):
                    raise ExitConditionError("Only direct function calls allowed")

    def _validate_symbols(self, tree: ast.AST):
        """
        Ensure all referenced names are registered.
        """
        allowed_names = {
            "artifact",
            "ctx",
            *self.function_registry.keys(),
            *self.variable_registry.keys(),
            *self.ALLOWED_BUILTINS.keys(),
            "True",
            "False",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if node.id not in allowed_names:
                    raise ExitConditionError(
                        f"Unregistered symbol in exit condition: '{node.id}'"
                    )

