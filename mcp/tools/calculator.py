import agents.tools.tool as Tool
from tools.mcp_server import mcp

class CalculatorTool(Tool):
    def run(self, expression):
        return eval(expression)

