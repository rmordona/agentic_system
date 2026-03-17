from __future__ import annotations
from core.paths import DOMAIN_ROOT

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

    def __init__(self, domain_name: str, role_name: str):

        self.domain_name = domain_name
        self.domain_path = DOMAIN_ROOT / domain_name

        self.role_name = role_name

        # Instantiate PredicateEngine for normalization only
        self.engine = PredicateEngine()

        self._predicates: Dict[str, Callable[[StageEvalContext], bool]] = {}
        self.initialize()

        self.evaluator = ExitConditionEvaluator(
            function_registry=self._predicates,
            variable_registry=self.VARIABLES,
        )

    def initialize(self):
        module = importlib.import_module(
            f"domain.{self.domain_name}.roles.{self.role_name}.tools.predicates"
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

    def normalize(self, expr: str) -> str:
        """
        Expose normalization for StageManager or other code.
        """
        return self.engine.normalize_expression(expr)

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

    # Mapping human phrases to Python operators
    DSL_MAPPING = {
        " is set": " != None",
        " is not set": " == None",
        " is True": " == True",
        " is False": " == False",
        " is between ": " BETWEEN ",
        " is greater than ": " > ",
        " is less than ": " < ",
        " is at least ": " >= ",
        " contains ": " CONTAINS ",
        " matches ": " == ",
        " conflicts with ": " != ",
        " is ": " == "
    }

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

    def normalize_expression(self, expr: str) -> str:
        """
        Translates human-readable spec into a Python-evaluable string.

        Example:
        'vix is greater than VIX_MAX'
            -> 'ctx.vix > VIX_MAX'

        'macro_analysis.risk_index is between [1,10]'
            -> '(ctx.macro_analysis.risk_index >= 1 and ctx.macro_analysis.risk_index <= 10)'
        """

        normalized = expr.strip()

        # --------------------------------------------------
        # Normalize logical operators
        # --------------------------------------------------

        normalized = re.sub(r"\bAND\b", "and", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bOR\b", "or", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bNOT\b", "not", normalized, flags=re.IGNORECASE)

        # --------------------------------------------------
        # BETWEEN syntax
        # macro_analysis.risk_index between [1,10]
        # --------------------------------------------------

        between_pattern = re.compile(
            r"([\w\.]+)\s+(?:is\s+)?between\s+\[\s*([0-9\.]+)\s*,\s*([0-9\.]+)\s*\]",
            flags=re.IGNORECASE
        )

        def between_repl(match):
            field = match.group(1)
            low = match.group(2)
            high = match.group(3)

            field = self._prepend_ctx(field)

            return f"({field} >= {low} and {field} <= {high})"

        normalized = between_pattern.sub(between_repl, normalized)

        # --------------------------------------------------
        # Apply DSL phrase mapping
        # --------------------------------------------------

        for human, code in self.DSL_MAPPING.items():
            normalized = re.sub(
                re.escape(human),
                code,
                normalized,
                flags=re.IGNORECASE
            )

        # --------------------------------------------------
        # Prepend ctx to variables
        # --------------------------------------------------

        def prepend_ctx(match):

            word = match.group(0)

            if (
                word.startswith("ctx.") or
                word.isupper() or
                word.isdigit() or
                word in ["True", "False", "None", "and", "or", "not"]
            ):
                return word

            return f"ctx.{word}"

        normalized = re.sub(
            r"\b[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*\b",
            prepend_ctx,
            normalized,
            flags=re.IGNORECASE
        )

        logger.info(f"Normalized expression: {normalized}")

        return normalized

    def _prepend_ctx(self, field: str) -> str:

        if field.startswith("ctx."):
            return field

        if field.split(".")[0].isupper():
            return field

        return f"ctx.{field}"

#############################################################################################
# Predicate Decorator - Required by Assistances ./workspaces/<assistants/tools/predicates.py
#############################################################################################
class Predicates:
    @staticmethod
    def policy(name: str | None = None):
        def decorator(fn):
            fn.__policy_name__ = name or fn.__name__
            return fn
        return decorator

    @staticmethod
    def process(ctx: StageEvalContext) -> dict:
        logger.info(f"ctx.task: {ctx.task}")
        task_result = ctx.task.get("result")
        logger.info(f"Task Result: {task_result}")
        data = task_result.get("output")
        return data


################################################################################
# Exit Condition Engine
################################################################################

class ExitConditionError(Exception):
    pass


class ExitConditionEvaluator:
    """
    AST-safe, domain-agnostic policy expression evaluator.

    Features:
    - Allows safe attribute access (e.g., ctx.macro_analysis.risk_index)
    - Supports AND/OR/NOT and comparison operators
    - Prevents unsafe/magic attribute access
    - Sandbox evaluation with restricted builtins and registered policies
    """

    # Allowed AST nodes
    ALLOWED_NODES = {
        ast.Expression,
        ast.BoolOp,
        ast.Compare,
        ast.Call,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.Attribute,
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
        # --- ADD THESE FOR 'CONTAINS' SUPPORT ---
        ast.List,           # To handle the ["a", "b"] part
        ast.GeneratorExp,   # To handle the 'for item in' part
        ast.comprehension,   # To handle the iteration logic
        ast.In,
        ast.Load,
        ast.Store
    }

    # Builtin functions safe to expose
    ALLOWED_BUILTINS = {
        "len": len,
        "any": any,
        "all": all,
        "sum": sum,
        "min": min,
        "max": max,
    }

    # Names allowed in policies by default
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
            logger.info(f"Compiling exit condition: {expr}")
            tree = ast.parse(expr, mode="eval")
        except SyntaxError as e:
            raise ExitConditionError(f"Invalid syntax: {e}")

        self._validate_ast(tree)
        self._validate_symbols(tree)
        return tree
        
    
    @staticmethod
    def _normalize_expression(expr: str) -> str:
        """
        Normalize natural language predicates into Python expressions.
        Supports numbers, BETWEEN, and CONTAINS logic.
        """

        normalized = expr.strip()

        # ------------------------------------------------
        # 1. Logical operators
        # ------------------------------------------------
        normalized = (
            normalized.replace("||", " or ")
            .replace("&&", " and ")
            .replace("!(", " not (")
            .replace("! ", " not ")
        )

        # ------------------------------------------------
        # Helper: convert numeric string possibly containing %
        # ------------------------------------------------
        def normalize_number(value: str) -> str:
            value = value.strip()
            if value.endswith("%"):
                return str(float(value[:-1]) / 100)
            return value

        # ------------------------------------------------
        # 2. BETWEEN expressions
        # ------------------------------------------------
        num_pattern = r"\d+(?:\.\d+)?%?"
        between_pattern = rf"(\S+)\s+(?:is\s+)?between\s+\[\s*({num_pattern})\s*,\s*({num_pattern})\s*\]"

        def replace_between(match):
            var = match.group(1)
            low = normalize_number(match.group(2))
            high = normalize_number(match.group(3))
            return f"{low} <= {var} <= {high}"

        normalized = re.sub(between_pattern, replace_between, normalized, flags=re.IGNORECASE)

        # ------------------------------------------------
        # 3. CONTAINS Logic (The New Addition)
        # Handles: var contains ["item1", "item2"]
        # ------------------------------------------------
        contains_pattern = r"(\S+)\s+contains\s+\[(.*?)\]"

        def replace_contains(match):
            var = match.group(1)
            # Capture the internal list content (e.g., '"ctx.sector", "ctx.volatility"')
            items_content = match.group(2)
            # Pythonic way to check multiple keys: all(x in var for x in [list])
            return f"all(item in {var} for item in [{items_content}])"

        normalized = re.sub(contains_pattern, replace_contains, normalized, flags=re.IGNORECASE)

        # ------------------------------------------------
        # 4. Comparison phrases
        # ------------------------------------------------
        comparison_patterns = {
            r"(?:is\s+)?greater\s+than": ">",
            r"(?:is\s+)?more\s+than": ">",
            r"(?:is\s+)?above": ">",
            r"(?:is\s+)?less\s+than": "<",
            r"(?:is\s+)?lesser\s+than": "<",
            r"(?:is\s+)?below": "<",
            r"matches": "==",
            r"conflicts with": "!=",
        }

        for phrase, op in comparison_patterns.items():
            pattern = rf"(\S+)\s+{phrase}\s+(\S+)" # Modified to accept strings or numbers

            def replace_comp(match):
                var = match.group(1)
                val = normalize_number(match.group(2))
                return f"{var} {op} {val}"

            normalized = re.sub(pattern, replace_comp, normalized, flags=re.IGNORECASE)

        # ------------------------------------------------
        # 5. 'is set' and 'exists' handling
        # ------------------------------------------------
        normalized = re.sub(
            r"(\S+)\s+(?:is\s+set|exists)",
            r"\1 is not None",
            normalized,
            flags=re.IGNORECASE
        )

        return normalized

    # -------------------------------------------------------------------------
    # Evaluate
    # -------------------------------------------------------------------------

    def evaluate(self, compiled_expr: ast.Expression, ctx_obj: Any) -> bool:
        """
        Evaluate compiled AST expression in a sandbox with safe context.
        """
        context = {
            "__builtins__": {},
            "ctx": ctx_obj,
            "artifact": getattr(ctx_obj, "artifact", {}),
            **self.ALLOWED_BUILTINS,
            **self.function_registry,
            **self.variable_registry,
        }

        self._inject_domain_variables(context, ctx_obj)

        try:
            return bool(eval(compile(compiled_expr, "<exit_condition>", "eval"), context))
        except Exception as e:
            logger.error(f"Error evaluating exit condition: {e}")
            return False

    # -------------------------------------------------------------------------
    # AST Validation
    # -------------------------------------------------------------------------

    def _validate_ast(self, tree: ast.AST):
        for node in ast.walk(tree):
            if not isinstance(node, tuple(self.ALLOWED_NODES)):
                raise ExitConditionError(f"Disallowed AST node: {type(node).__name__}")

            # Allow attribute access but disallow magic attributes
            if isinstance(node, ast.Attribute):
                chain = self._resolve_attr_chain(node)
                for part in chain:
                    if part.startswith("__"):
                        raise ExitConditionError(
                            f"Access to magic attribute '{part}' is forbidden"
                        )

            if isinstance(node, ast.Call) and not isinstance(node.func, ast.Name):
                raise ExitConditionError("Only direct function calls allowed")

    def _resolve_attr_chain(self, node: ast.Attribute) -> list[str]:
        """
        Recursively extract attribute chain from AST node.
        Example: ctx.macro_analysis.risk_index -> ['ctx', 'macro_analysis', 'risk_index']
        """
        attrs = []
        while isinstance(node, ast.Attribute):
            attrs.insert(0, node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            attrs.insert(0, node.id)
        else:
            raise ExitConditionError(f"Unsupported node in attribute chain: {type(node).__name__}")
        return attrs

    # -------------------------------------------------------------------------
    # Symbol Validation
    # -------------------------------------------------------------------------

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
                raise ExitConditionError(f"Invalid domain variable '{name}'")
        self._last_domain_vars = domain_vars

    # -------------------------------------------------------------------------
    # Runtime domain variable injection
    # -------------------------------------------------------------------------

    def _inject_domain_variables(self, context: Dict[str, Any], ctx_obj: Any):
        """
        Inject domain variables into the evaluation context safely.
        """
        symbols = getattr(ctx_obj, "symbols", lambda: {})()
        for name in self._last_domain_vars:
            if name in symbols:
                context[name] = symbols[name]
            else:
                raise ExitConditionError(f"Domain variable '{name}' not found in context")