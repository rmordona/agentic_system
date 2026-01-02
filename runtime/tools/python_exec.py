import asyncio
from runtime.tools.base import Tool


class PythonExecTool(Tool):
    def __init__(self, spec: dict):
        self.name = spec["name"]
        self.description = spec["description"]

    async def call(self, code: str):
        proc = await asyncio.create_subprocess_exec(
            "python",
            "-c",
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
        }

