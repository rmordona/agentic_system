class LLMInterface:
    def generate(self, prompt: str) -> dict:
        raise NotImplementedError

