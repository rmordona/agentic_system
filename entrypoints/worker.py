# entrypoints/worker.py
from runtime.runtime import Runtime

runtime = Runtime()

async def handle_job(job):
    await runtime.run(job["task"])

