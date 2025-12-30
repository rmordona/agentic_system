class Runtime:
    def __init__(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        orchestrator=None,
        hitl_callback=None
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.hitl_callback = hitl_callback
        self.orchestrator = orchestrator


    async def run(self, task: str):

        return await self.orchestrator.run(
            session_id=self.session_id,
            task=task
        )


