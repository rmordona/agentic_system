"""
base.py

Defines the BaseAgent class for the agentic system.

Responsibilities:
- Provide common LLM integration
- Handle prompt building
- Support multiple output modes: text or JSON/schema
- Emit events to EventBus
- Support tool calls if needed
- Compatible with stage constraints enforced by Orchestrator/LangGraph
"""

import json
import re
from pathlib import Path
from abc import ABC, abstractmethod
import jsonschema
from graph.state import State, AgentOutput

import asyncio
from llm.local_llm import LocalLLM

class BaseAgent(ABC):
    """
    Base agent supporting:
    - Prompt templates (.md)
    - Schema validation (.json)
    - LLM calls
    - Tool calls and event reporting
    """

    CONTROL_FIELDS = {"stage", "done", "decision", "winner"}

    def __init__(self, role:str, llm = LocalLLM, template_path: str = None, schema_path: str = None, output_mode="json"):
        """
        Args:
            role: agent role name
            llm: LLM interface (must implement generate())
            template_path: path to agent's prompt template
            schema_path: optional JSON schema path for validation
            output_mode: "json" for structured output or "text" for free text
        """   
        self.role = role
        self.template_path = Path(template_path)
        self.schema_path = Path(schema_path) if schema_path else None

        self.prompt_template = self._load_template()
        self.schema = self._load_json_schema()

        self.raw_schema = self._load_raw_schema()

        self.llm = llm    
        self.output_mode = output_mode
        self.event_bus = None

    async def _emit(self, event: str, payload: Dict[str, Any]):
        if self.event_bus:
            await self.event_bus.emit(event, payload)

    def _load_template(self):
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found: {self.template_path}")
        return self.template_path.read_text()

    def _load_json_schema(self):
        if self.schema_path and self.schema_path.exists():
            return json.loads(self.schema_path.read_text())
        return None

    def _load_raw_schema(self):
        if self.schema_path and self.schema_path.exists():
            return  self.schema_path.read_text()
        return None

    def build_prompt(self, task: str, context: str = "", category: str = "", episodic_summary: str = "") -> str:
        """
        Render the prompt template with dynamic variables:
        - {{task}}: the main task
        - {{conversation_history}}: history of previous rounds
        """
        prompt = self.prompt_template
        prompt = prompt.replace("{{task}}", task)
        prompt = prompt.replace("{{conversation_history}}", context)
        prompt = prompt.replace("{{schema}}", self.raw_schema)
        prompt = prompt.replace("{{category}}", category)
        prompt = prompt.replace("{{summary}}", episodic_summary)
        return prompt


    def _validate_output_keys(self, output: dict):
        illegal = self.CONTROL_FIELDS & output.keys()
        if illegal:
            raise RuntimeError(
                f"Agent '{self.role}' attempted to write control fields: {illegal}"
            )


    async def validate_output(self, output_json: dict):
        """Validate agent output against schema if available."""
        if self.schema:
            try:
                jsonschema.validate(instance=output_json, schema=self.schema)
            except jsonschema.ValidationError as e:
                raise ValueError(f"Output JSON does not match schema: {e}")

   
    @staticmethod
    def parse_json_from_text(text: str) -> dict:
        """Extract first JSON object from arbitrary text."""
        match = re.search(r'({.*})', text, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in LLM output")
        return json.loads(match.group(1))

    @staticmethod
    def parse_llm_json(output_str: str) -> Any:
        """
        Safely parse JSON coming from LLM / agent output.
        Handles:
        - empty strings
        - BOM characters
        - leading/trailing text
        - markdown / explanations
        """

        if output_str is None:
            raise JSONParseError("LLM output is None")

        if not isinstance(output_str, str):
            raise JSONParseError(f"Expected str, got {type(output_str)}")

        # Strip whitespace + BOM
        text = output_str.lstrip("\ufeff").strip()

        if not text:
            raise JSONParseError("LLM output is empty after stripping")

        # Fast path: pure JSON
        if text.startswith("{") and text.endswith("}"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass  # fall back to extraction

        # Extract first JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise JSONParseError(
                f"No JSON object found in output:\n{repr(text[:200])}"
            )

        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as e:
            raise JSONParseError(
                f"JSON parsing failed: {e}\nExtracted JSON:\n{match.group(0)[:500]}"
            )

    @abstractmethod
    async def _process(self, state):
        """Subclasses implement agent-specific logic"""
        pass # pass to subclasses

    async def run(self, state):

        await self._emit("agent_start", {"agent": self.role })


        output = await self._process(state)

        if not isinstance(output, dict):
            raise TypeError(f"Agent '{self.role}' must return a state, got {type(output)}")

        # Validate control fields
        self._validate_output_keys(output)

        print("In Base code, in run() !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"state: {state}")
        print(f"output: {output}")

        await self._emit("agent_done", {"agent": self.role, "output": output})

        return output

    async def generate(self, prompt: str) ->str:
        if self.llm:
            print("In Base Code, generating llm response !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("Prompt being used to generate ...")
            return await self.llm.generate(prompt)
        return f'{{"title": "Simulated Idea", "core_idea": "Simulated core idea", "features": ["feature1"], "win_rationale": "Simulated rationale"}}'

    # Pass state in the payload
    async def call_tool(self, tool_name: str, payload: dict):
        if self.event_bus:
            await self.event_bus.emit("tool_call", {"agent": self.role, "tool": tool_name, "payload": payload})

