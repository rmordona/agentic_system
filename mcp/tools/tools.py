class Tool:
    def __init__(self, name):
        self.name = name

    async def run(self, args: dict, state: dict):
        raise NotImplementedError("Tool must implement run method")

