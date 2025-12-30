import json
from pathlib import Path
from string import Template
from jsonschema import validate

class BaseAgent:
    def __init__(self, name, prompt_path, schema_path, llm):
        self.name = name
        self.prompt_template = Template(Path(prompt_path).read_text())
        self.schema = json.loads(Path(schema_path).read_text())
        self.llm = llm

    def build_prompt(self, task, history):
        return self.prompt_template.substitute(
            task=task,
            conversation_history=history or "No prior context."
        )

    def run(self, task, history):
        prompt = self.build_prompt(task, history)
        response = self.llm.generate(prompt)
        validate(instance=response, schema=self.schema)
        return response

