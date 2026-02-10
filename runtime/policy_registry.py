import re
import ast
import json
import inspect
import importlib
from pathlib import Path
from typing import Any, Callable, Dict, Set, Union

from dataclasses import dataclass

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")


################################################################################
# Evaluation Context
################################################################################

@dataclass(frozen=True)
class StageEvalContext:
    task: dict
    artifact: dict
    data: dict
    tools: list
    hitl_flags: dict
    stage: str

    def symbols(self) -> Dict[str, Any]:
        """
        Flattened symbol table exposed to policy expressions.
        This is the ONLY place domain variables come from.
        """
        symbols: Dict[str, Any] = {}

        if isinstance(self.data, dict):
            symbols.update(self.data)

        if isinstance(self.hitl_flags, dict):
            symbols.update(self.hitl_flags)

        if isinstance(self.artifact, dict):
            symbols.update(self.artifact)

        return symbols


################################################################################
# Policy Registry
################################################################################

class PolicyRegistry:

    VARIABLES = {
        "hitl_approved": False,
        "hitl_approval": False,
        "human_abort_confirmed": False,
    }

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.workspace_name = workspace_path.name

        self._predicates: Dict[str, Callable[[StageEvalContext], bool]] = {}
        self.initialize()

        self.evaluator = ExitConditionEvaluator(
            function_registry=self._predicates,
            variable_registry=self.VARIABLES,
        )

    def initialize(self):
        module = importlib.import_module(
            f"workspaces.{self.workspace_name}.tools.predicates"
        )
        Policies = getattr(module, "Policies")
        self.register_from_class(Policies)

    def register_from_class(self, cls: type, prefix: str | None = None):
        logger.info(f"Registering policies from class {cls.__name__}")

        for _, attr in vars(cls).items():
            if not callable(attr):
                continue

            if not hasattr(attr, "__policy_name__"):
                continue

            sig = inspect.signature(attr)
            if len(sig.parameters) != 1:
                raise ValueError(
                    f"Policy '{attr.__name__}' must accept exactly one argument (ctx)"
                )

            name = attr.__policy_name__
            key = f"{prefix}.{name}" if prefix else name
            self._predicates[key] = attr

        self.list_registered_policies()

    def list_registered_policies(self):
        for name in self._predicates:
            logger.info(f"Registered predicate: {name}")

    def compile(self, expr: str) -> ast.Expression:
        return self.evaluator.compile(expr)

    def evaluate(
        self,
        compiled_expr: ast.Expression,
        artifact: dict,
        state_ctx: dict | None = None,
    ) -> bool:
        ctx_obj = StageEvalContext(
            task=state_ctx.get("task"),
            artifact=artifact,
            data=state_ctx.get("data", {}) if state_ctx else {},
            tools=state_ctx.get("recent_tools", []) if state_ctx else [],
            hitl_flags=state_ctx.get("workflow_metadata", {}).get("hitl_flags", {})
            if state_ctx
            else {},
            stage=state_ctx.get("stage", "unknown") if state_ctx else "unknown",
        )
        return self.evaluator.evaluate(compiled_expr, ctx_obj)

################################################################################
# Predicate Translator and Evaluator
################################################################################
class PredicateEngine:
    """
    Unified validation engine:
    - Phase 1: Parse string predicates into JSON logic
    - Phase 2: Evaluate JSON logic against context dict
    """

    OP_MAP = {
        ast.Gt: ">",
        ast.Lt: "<",
        ast.GtE: ">=",
        ast.LtE: "<=",
        ast.Eq: "==",
        ast.NotEq: "!=",
        ast.In: "in"
    }

    def __init__(self):
        # Atomic operations for verification
        self._logic_ops = {
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            ">":  lambda a, b: a > b,
            "<":  lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
            "in": lambda a, b: a in b,
            "exists": lambda a, _: a is not None
        }

    # ----------------------
    # PHASE 1: STRING -> JSON
    # ----------------------
    def parse_predicate(self, expr: Union[str, dict]) -> dict:
        """
        Converts string predicates into JSON gate.
        Supports:
        - "field exists"
        - standard comparisons with AND/OR
        - nested fields using dot notation
        """
        if isinstance(expr, dict):
            return expr  # already JSON

        expr = expr.strip()

        # --- Special case: 'exists' ---
        if re.match(r".+ exists$", expr):
            field_name = expr.split()[0]
            return {"field": field_name, "op": "exists", "value": True}

        # --- Normal Python expressions ---
        clean_expr = expr.replace(" AND ", " and ").replace(" OR ", " or ")
        try:
            tree = ast.parse(clean_expr, mode="eval")
            return self._node_to_dict(tree.body)
        except Exception as e:
            raise ValueError(f"Failed to parse predicate string '{expr}': {e}")

    def _node_to_dict(self, node):
        if isinstance(node, ast.BoolOp):
            op_key = "and" if isinstance(node.op, ast.And) else "or"
            return {op_key: [self._node_to_dict(v) for v in node.values]}

        if isinstance(node, ast.Compare):
            if len(node.ops) > 1:
                raise ValueError("Chained comparisons not supported")

            left = self._resolve_name(node.left)
            op_type = type(node.ops[0])
            op = self.OP_MAP.get(op_type)
            if op is None:
                raise ValueError(f"Unsupported operator: {op_type}")

            right = ast.literal_eval(node.comparators[0])
            return {"field": left, "op": op, "value": right}

        raise ValueError(f"Unsupported AST node type: {type(node).__name__}")

    def _resolve_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._resolve_name(node.value)}.{node.attr}"
        raise ValueError(f"Unsupported node for field name: {type(node).__name__}")

    # ----------------------
    # PHASE 2: EVALUATION
    # ----------------------
    def verify(self, gate: dict, context: dict) -> bool:
        """
        Recursively evaluate the JSON gate against a context dictionary.
        """
        # Logical AND
        if "and" in gate:
            return all(self.verify(sub, context) for sub in gate["and"])

        # Logical OR
        if "or" in gate:
            return any(self.verify(sub, context) for sub in gate["or"])

        # Atomic gate
        field_path = gate.get("field")
        op = gate.get("op", "exists")
        expected = gate.get("value")

        actual = context
        try:
            for key in field_path.split('.'):
                actual = actual[key] if isinstance(actual, dict) else None
        except (KeyError, TypeError):
            actual = None

        operation = self._logic_ops.get(op)
        if not operation:
            raise ValueError(f"Unknown operator: {op}")

        try:
            return operation(actual, expected)
        except Exception:
            return False


################################################################################
# Predicate Decorator
################################################################################

class Predicates:
    @staticmethod
    def policy(name: str | None = None):
        def decorator(fn):
            fn.__policy_name__ = name or fn.__name__
            return fn
        return decorator

    @staticmethod
    def process(ctx: StageEvalContext) -> dict:
        logger.info(f"ctx: {ctx}")
        task_result = ctx.task.result
        logger.info(f"Task Result: {task_result}")
        output = task_result.output
        logger.info(f"Task Result Output: {output}")

        text_content_obj = output[0]
        raw_text = text_content_obj.text

        data = json.loads(raw_text)
        return data


################################################################################
# Exit Condition Engine
################################################################################

class ExitConditionError(Exception):
    pass


class ExitConditionEvaluator:
    """
    AST-safe, domain-agnostic policy expression evaluator.
    """

    ALLOWED_NODES = {
        ast.Expression,
        ast.BoolOp,
        ast.Compare,
        ast.Call,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.And,
        ast.Or,
        ast.Eq,
        ast.NotEq,
        ast.Gt,
        ast.GtE,
        ast.Lt,
        ast.LtE,
        ast.UnaryOp,
        ast.Not,
    }

    ALLOWED_BUILTINS = {
        "len": len,
        "any": any,
        "all": all,
        "sum": sum,
        "min": min,
        "max": max,
    }

    STATIC_SYMBOLS = {
        "ctx",
        "artifact",
        "True",
        "False",
    }

    def __init__(
        self,
        function_registry: Dict[str, Callable],
        variable_registry: Dict[str, Any] | None = None,
    ):
        self.function_registry = function_registry
        self.variable_registry = variable_registry or {}
        self._last_domain_vars: Set[str] = set()

    # -------------------------------------------------------------------------
    # Compile
    # -------------------------------------------------------------------------

    def compile(self, expression: str) -> ast.Expression:
        expr = self._normalize_expression(expression)

        try:
            logger.info(f"Expression to parse: {expr}")
            tree = ast.parse(expr, mode="eval")
        except SyntaxError as e:
            raise ExitConditionError(f"Invalid exit condition syntax: {e}")

        self._validate_ast(tree)
        self._validate_symbols(tree)

        return tree

    @staticmethod
    def _normalize_expression(expr: str) -> str:
        return (
            expr.replace("||", " or ")
                .replace("&&", " and ")
                .replace("!", " not ")
        )

    # -------------------------------------------------------------------------
    # Evaluate
    # -------------------------------------------------------------------------

    def evaluate(self, compiled_expr: ast.Expression, ctx_obj: StageEvalContext) -> bool:
        context = {
            "__builtins__": {},
            "ctx": ctx_obj,
            "artifact": ctx_obj.artifact,
            **self.ALLOWED_BUILTINS,
            **self.function_registry,
            **self.variable_registry,
        }

        self._inject_domain_variables(context, ctx_obj)

        return bool(
            eval(compile(compiled_expr, "<exit_condition>", "eval"), context)
        )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def _validate_ast(self, tree: ast.AST):
        for node in ast.walk(tree):
            if not isinstance(node, tuple(self.ALLOWED_NODES)):
                raise ExitConditionError(
                    f"Disallowed AST node: {type(node).__name__}"
                )

            if isinstance(node, ast.Call) and not isinstance(node.func, ast.Name):
                raise ExitConditionError("Only direct function calls allowed")

            if isinstance(node, ast.Attribute):
                raise ExitConditionError("Attribute access is not allowed")

    def _extract_names(self, tree: ast.AST) -> Set[str]:
        return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}

    def _validate_symbols(self, tree: ast.AST):
        referenced = self._extract_names(tree)

        allowed = (
            self.STATIC_SYMBOLS
            | set(self.function_registry.keys())
            | set(self.variable_registry.keys())
            | set(self.ALLOWED_BUILTINS.keys())
        )

        domain_vars = referenced - allowed

        for name in domain_vars:
            if name.startswith("_"):
                raise ExitConditionError(
                    f"Invalid domain variable '{name}'"
                )

        self._last_domain_vars = domain_vars

    # -------------------------------------------------------------------------
    # Runtime variable injection
    # -------------------------------------------------------------------------

    def _inject_domain_variables(
        self,
        context: Dict[str, Any],
        ctx_obj: StageEvalContext,
    ):
        symbols = ctx_obj.symbols()

        for name in self._last_domain_vars:
            if name in symbols:
                context[name] = symbols[name]
            else:
                raise ExitConditionError(
                    f"Domain variable '{name}' not found in evaluation context"
                )
