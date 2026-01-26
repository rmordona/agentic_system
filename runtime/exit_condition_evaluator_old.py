import ast
from typing import Any, Callable, Dict


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
        artifact: dict,
        state: dict | None = None,
    ) -> bool:
        """
        Evaluate a previously compiled exit condition.
        """

        context = {
            "__builtins__": {},
            "artifact": artifact,
            "ctx" : ctx,
            **self.ALLOWED_BUILTINS,
            **self.function_registry,
            **self.variable_registry,
        }

        if state:
            context.update(state)

        try:
            return bool(eval(compile(compiled_expr, "<exit_condition>", "eval"), context))
        except Exception as e:
            raise ExitConditionError(f"Exit condition evaluation failed: {e}")

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

