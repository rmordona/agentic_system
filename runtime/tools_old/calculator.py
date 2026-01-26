import ast
from runtime.tools.base import Tool


class CalculatorTool(Tool):
    def __init__(self, spec: dict):
        self.name = spec["name"]
        self.description = spec["description"]

    async def call(self, expression: str):
        node = ast.parse(expression, mode="eval")
        for n in ast.walk(node):
            if not isinstance(n, (ast.Expression, ast.BinOp, ast.Num, ast.Add, ast.Sub, ast.Mult, ast.Div)):
                raise ValueError("Unsafe expression")
        return {"result": eval(compile(node, "<calc>", "eval"))}

