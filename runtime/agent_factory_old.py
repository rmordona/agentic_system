# -----------------------------------------------------------------------------
# Project: Agentic System
# File: runtime/agents/agent_factory.py
#
# Description:
#   This module defines the canonical compilation and execution pipeline for
#   agent specifications authored in Markdown (AGENT.md).
#
#   It is intentionally:
#     - Agent-agnostic
#     - Model-agnostic
#     - Tool-agnostic
#
#   The system enforces a strict chain of custody:
#
#     AGENT.md (human policy)
#        ↓ deterministic parsing
#     AgentSchema (validated contract)
#        ↓ controlled binding
#     AgentRunner (execution scaffold)
#
#   This module does NOT:
#     - Encode domain-specific behavior
#     - Make assumptions about agent purpose (critic, planner, executor, etc.)
#     - Decide when or how an LLM is invoked
#
#   Instead, it provides:
#     - Deterministic compilation of agent policy into machine-validated schema
#     - Structural guarantees via Pydantic
#     - Observable, auditable execution scaffolding
#
#   AGENT.md is POLICY
#   AgentSchema is CONTRACT
#   AgentRunner is MECHANISM
#
# Production Guarantees:
#   - Fully deterministic compilation
#   - Explicit schema validation
#   - Cryptographic source hashing
#   - Structured logging for audit and debugging
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-01
# -----------------------------------------------------------------------------

import mistune
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel, Field

from langchain_core.prompts import PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from llm.model_manager import ModelManager
from runtime.stage_registry import StageRegistry
from runtime.tool_registry import ToolRegistry

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")

# -------------------------------------------------------------------------
# 1. Validated Schema (Canonical Agent Contract)
# -------------------------------------------------------------------------

class AgentSchema(BaseModel):
    """
    Machine-enforceable representation of an agent definition.

    This schema is the ONLY structure downstream systems should trust.
    """

    agent_id: str
    intent: str
    role: str
    role_summary: str
    authority: str
    judgment_posture: str
    constraints: List[str]

    inputs: Dict[str, bool] = {
        "task": True,
        "conversation_history": True,
        "artifact": True
    }

    outputs: List[str]
    skills: List[str]

    version: str = "1.0.0"
    compiled_at: str
    source_hash: str

    def get_id(self) -> str:
        return self.agent_id


# -------------------------------------------------------------------------
# 2. Agent Factory (Markdown → Schema Compiler)
# -------------------------------------------------------------------------

class AgentFactory:
    """
    Compiles AGENT.md files into validated AgentSchema objects.

    This class performs:
      - Markdown parsing
      - Semantic section extraction
      - Deterministic normalization
      - Cryptographic hashing
      - Schema validation
    """

    def __init__(self, workspace_path: str):
        # renderer=None returns the AST (Abstract Syntax Tree)
        self.parser = mistune.create_markdown(renderer=None)
        logger.info("AgentFactory initialized")

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _extract_text_recursive(self, node) -> str:
        """Recursively extracts raw text from nested Mistune AST nodes."""
        if "text" in node:
            return node["text"]
        if "children" in node:
            return "".join(self._extract_text_recursive(c) for c in node["children"])
        return ""

    def _get_sections(self, md_text: str) -> Dict[str, str]:
        """
        Groups Markdown content by normalized heading names.

        Example:
          ## Judgment Posture → judgment_posture
        """
        ast = self.parser(md_text)
        sections: Dict[str, str] = {}
        current_heading = "preamble"

        for node in ast:
            if node["type"] == "heading":
                current_heading = (
                    self._extract_text_recursive(node)
                    .lower()
                    .strip()
                    .replace(" ", "_")
                )
                sections[current_heading] = ""
                logger.debug("Discovered section", extra={"section": current_heading})

            elif node["type"] in ["paragraph", "list", "block_code", "text"]:
                content = self._extract_text_recursive(node)
                sections[current_heading] = sections.get(current_heading, "") + "\n" + content

        return sections

    def _extract_list(self, section_text: str) -> List[str]:
        """
        Semantic extraction of bullet points from a section.

        Falls back to newline splitting if bullets are not present.
        """
        items = re.findall(r"^\s*[-*•]\s*(.*)$", section_text, re.MULTILINE)
        if not items:
            items = [line.strip() for line in section_text.split("\n") if line.strip()]
        return [i.strip() for i in items if i.strip()]

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    def compile(self, agent_id: str, agent_md_path: str) -> AgentSchema:
        """
        Deterministically compiles an AGENT.md file into an AgentSchema.

        This is a pure transformation:
          input  → markdown
          output → validated schema
        """
        path = Path(agent_md_path)

        if not path.exists():
            logger.error("Agent spec not found", extra={"path": agent_md_path})
            raise FileNotFoundError(f"Agent spec not found at {agent_md_path}")

        logger.info("Compiling agent", extra={"agent_id": agent_id})

        text = path.read_text(encoding="utf-8")
        sections = self._get_sections(text)

        agent_dict = {
            "agent_id": agent_id,
            "intent": sections.get("intent", "No intent defined.").strip(),
            "role": sections.get("role", agent_id),
            "role_summary": sections.get(
                "role_summary",
                sections.get("role", "")
            ).strip(),
            "authority": sections.get(
                "authority",
                "General execution authority."
            ).strip(),
            "judgment_posture": sections.get(
                "judgment_posture",
                "Objective"
            ).strip(),
            "constraints": self._extract_list(sections.get("constraints", "")),
            "inputs": {
                "task": True,
                "conversation_history": True,
                "artifact": True
            },
            "outputs": self._extract_list(sections.get("outputs", "")),
            "skills": self._extract_list(
                sections.get("skills", sections.get("capabilities", ""))
            ),
            "version": "1.0.0",
            "compiled_at": datetime.utcnow().isoformat() + "Z",
            "source_hash": self._hash(text)
        }

        logger.debug(
            "Agent compilation payload prepared",
            extra={"agent_id": agent_id, "keys": list(agent_dict.keys())}
        )

        schema = AgentSchema(**agent_dict)

        logger.info(
            "Agent compiled successfully",
            extra={
                "agent_id": agent_id,
                "source_hash": schema.source_hash[:8]
            }
        )

        return schema

    def save_json(self, agent_id: str, md_path: str, output_dir: str):
        """
        Compiles and persists the agent schema as JSON.
        """
        agent_obj = self.compile(agent_id, md_path)
        output_path = Path(output_dir) / f"{agent_id}.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(agent_obj.json(indent=2))

        logger.info(
            "Agent JSON written",
            extra={"agent_id": agent_id, "path": str(output_path)}
        )

        return output_path


# -------------------------------------------------------------------------
# 3. Agent Runner (Execution Scaffold)
# -------------------------------------------------------------------------
################################################################################
# The Flight Control Analogy: LLMs, Runners, and Tools
#
# In an agentic architecture, responsibility is deliberately separated
# to ensure safety, clarity, and control.
#
# The system can be understood through an aviation analogy:
#
#   - The LLM is the Pilot
#   - The AgentRunner is the Cockpit
#   - The Tools are the Engines and Control Surfaces
#
# ---------------------------------------------------------------------------
# Roles and Responsibilities
#
# The Pilot (LLM):
#   - Interprets intent and context
#   - Decides *what* should be done
#   - Issues high-level commands
#   - Never touches hardware directly
#
# Example:
#   "Lower the flaps."
#
# The Cockpit (AgentRunner):
#   - Translates pilot intent into validated actions
#   - Enforces constraints, permissions, and sequencing
#   - Selects the correct tools for the situation
#   - Prevents unsafe or unauthorized operations
#
# The Engines & Flaps (Tools):
#   - Perform the actual physical or computational work
#   - Are tightly coupled to a specific system or body
#   - Expose narrow, well-defined interfaces
#   - Do not make decisions
#
# ---------------------------------------------------------------------------
# Why This Separation Matters
#
# - The Pilot can be replaced or upgraded without rewiring the aircraft
# - The Cockpit guarantees procedural correctness and safety
# - Tools remain simple, testable, and deterministic
#
# This design ensures that:
#   - Reasoning does not imply authority
#   - Authority does not imply execution
#   - Execution does not imply judgment
#
# In short:
#   The LLM decides.
#   The Runner governs.
#   The Tools act.
################################################################################

class AgentRunner:
    """
    Lightweight execution scaffold for an agent.

    This class:
      - Assembles system prompts from schema
      - Enforces input gates
      - Restricts tool access to declared skills

    It does NOT:
      - Decide model choice
      - Implement reasoning logic
      - Enforce safety or policy rules
    """

    def __init__(self, schema: AgentSchema, tool_registry: ToolRegistry):
        self.schema = schema
        self.tool_registry = tool_registry

        logger.info(
            "AgentRunner initialized",
            extra={"agent_id": schema.agent_id}
        )

    def set_system_template(system_template: str):
        self.system_template = system_template

    async def build_system_prompt(self, context: SessionContext, task_info: dict, agent_spec: dict) -> str:
        # Inject context-specific variables into the System Template

        system_prompt = await hydrate(self.system_template, {
            "AGENT_ROLE": agent_spec["role_description"],
            "DOMAIN" : agent_spec["domain"],
            "TASK": task_info["task"],
            "DATA_TYPE" : context.data_type,
        })
        return system_prompt

    async def run(self, context: SessionContext, system_template: str, task_info: dict, agent_spec: dict, tools: list):
        # 1. Build the prompt
        logger.info(f"Agent is executing ...")
        final_system_prompt = await self.build_system_prompt(context, task_info, agent_spec)
        
        # Inside AgentRunner.run()
        envelope = DataEnvelope.model_validate_json(state["data_raw"])
        current_payload = envelope.payload  # This is your domain schema dict

        # Example: A booking tool that needs 'destination' and 'budget'
        # The Runner maps the payload keys to the tool arguments
        tool_output = await selected_tool.execute(
            destination=current_payload.get("destination"),
            limit=current_payload.get("budget_limit")
        )

        # 2. Call LLM with the Body (data_raw) and the Prompt
        # response = await llm.chat(system=final_system_prompt, user=context.data_raw, tools=tools)
        response = await _call_llm(prompt=final_system_prompt, user_intent=task_info, model_manager=self.model_manager)
        
        # 3. Return the new Data Plane and the Summary
        return response.new_data_raw, response.summary



    def run(self, task: str, artifact: str, history: list = None):
        """
        Assembles execution context and binds allowed tools.

        The actual LLM invocation is intentionally left abstract.
        """
        logger.info(
            "Executing agent",
            extra={
                "agent_id": self.schema.agent_id,
                "hash": self.schema.source_hash[:8]
            }
        )

        prompt_parts = [self._assemble_system_prompt()]

        if self.schema.inputs.get("task"):
            prompt_parts.append(f"Current Task: {task}")

        if self.schema.inputs.get("artifact"):
            prompt_parts.append(f"Target Artifact: {artifact}")

        if self.schema.inputs.get("conversation_history") and history:
            prompt_parts.append(f"History: {history}")

        allowed_tools = [
            self.tool_registry[s]
            for s in self.schema.skills
            if s in self.tool_registry
        ]

        logger.debug(
            "Bound tools for execution",
            extra={
                "agent_id": self.schema.agent_id,
                "tools": self.schema.skills
            }
        )

        # Placeholder for LLM execution
        # return llm.with_tools(allowed_tools).invoke("\n\n".join(prompt_parts))

        return "\n\n".join(prompt_parts)


    async def execute_tool_call(self, tool_call, state: StateSchema):
        # 1. Get the adapter for the current domain
        adapter = self.registry_loader.get_adapter(state["domain"])
        
        # 2. Parse the existing envelope
        old_envelope = DataEnvelope.model_validate_json(state["data_raw"])
        
        # 3. RUN THE TOOL
        # We pass the payload and the tool_call arguments
        tool_result = await self.tool_registry.call(
            tool_name=tool_call.name,
            args=tool_call.args,
            context=old_envelope.payload # The tool can 'read' the current data
        )

        # 4. UPDATE THE PAYLOAD
        # We merge the tool result back into the domain-specific payload
        updated_payload = {**old_envelope.payload, **tool_result.data}

        # 5. CREATE NEW ENVELOPE (The Handoff)
        new_envelope = adapter.create_envelope(
            payload=updated_payload,
            producer=self.agent.role,
            stage=state["stage"]
        )
        
        return new_envelope.model_dump_json()

# -------------------------------------------------------------------------
# 4. Plan Architect
# -------------------------------------------------------------------------
class PlanArchitect:
    def __init__(self, 
        workspace_path: str, 
        state_registry: StageRegistry,
        model_manager: ModelManager):

        logger.info("[PlanArchitect] Composing the artifact using ARCHITECT_TEMPLATE.md and PLAN_TEMPLATE.md")
        templates_dir = Path(workspace_path).parent / "system_templates"

        if not templates_dir.exists():
            logger.error(f"Workspace path '{templates_dir}' does not exist")
            raise FileNotFoundError(f"Workspace path '{templates_dir}' does not exist")

        # We load both templates
        self.architect_template = self.load_file(templates_dir / "ARCHITECT_TEMPLATE.md")
        self.plan_template = self.load_file(templates_dir / "PLAN_TEMPLATE.md")

        self.state_registry = state_registry
        self.first_stage = state_registry.first_stage()  
        self.first_stage_meta = state_registry.get(self.first_stage)
        self.first_stage_description = self.first_stage_meta.description
        self.stages = state_registry.list_stages()

        self.model_manager = model_manager

    def load_file(self, file_path: Path):

        if not file_path.exists():
            logger.error(f"File path '{file_path}' does not exist")
            raise FileNotFoundError(f"File path '{file_path}' does not exist")

        return file_path.read_text(encoding="utf-8")

    def _extract_tasks(self, raw_llm_text: str) -> str:
        """
        Filters the LLM response to include ONLY lines starting with '- [ ]'.
        """
        # Regex explanation: 
        # ^: Start of line
        # - \[ \]: Matches the literal characters '- [ ]'
        # .*: Matches everything else on that line
        task_pattern = r"^- \[ \].*"
        
        # We use re.MULTILINE to check every line in the string
        tasks = re.findall(task_pattern, raw_llm_text, re.MULTILINE)
        
        # Join them back into a single string for the template
        return "\n".join(tasks)

    async def build_initial_artifact(self, user_intent: str):

        # 1. Hydrate the INSTRUCTIONS (The System Prompt)
        logger.info("[PlanArchitect] Build Phase: Hydrating the system prompt.")
        logger.info(f"Meta Stage: {self.first_stage_meta}")
        logger.info(f"Stage Description: {self.first_stage_description}")
        system_prompt = await hydrate(self.architect_template, {
            "DOMAIN": "Universal Coordination",
            "USER_INTENT" : user_intent,
            "CURRENT_STAGE_NAME": self.first_stage,
            "CURRENT_STAGE_DESC" : self.first_stage_description,
            "AVAILABLE_STAGES" : list(self.stages),
            "PLAN_SECTION": "## CURRENT PLAN",
            "PREVIOUS_STAGE_OUTPUTS" : ""
        })
        logger.info(f"System Prompt: {system_prompt}")

        # 2. Get the RAW TASKS from the LLM
        # The LLM only sees the Instructions and the Goal.

        logger.info("LLM Model Call ...")
        raw_tasks = await _call_llm(prompt=system_prompt, user_intent=user_intent, model_manager=self.model_manager)

        logger.info("LLM Model Call complete ...")

        logger.info(f"Response: {raw_tasks.content}") 

        # 3. Inject the RAW TASKS into the SHELL (The Plan Template)
        logger.info("Now Hydrating the initial artifact.")
        initial_artifact = await hydrate(self.plan_template, {
            "MISSION_NAME": user_intent,
            "GENERATED_TASKS": self._extract_tasks(raw_tasks.content),
            "STATUS": "initialized",
            "SESSION_ID" : "Placeholder_Session_id",
            "INITIAL_TIMESTAMP" : "Placeholder_time"
        })

        logger.info("Initial Artifact:")
        logger.info(f"{initial_artifact}")

        return initial_artifact


# -------------------------------------------------------------------------
# Helper Function
# -------------------------------------------------------------------------
async def _call_llm(prompt: str, user_intent: str, model_manager: ModelManager) -> str:

    system_prompt = [
        HumanMessage(content=user_intent), # {"role" : "user", "content" : user_intent },
        SystemMessage(content=prompt)      # {"role" : "system", "content" : prompt }
    ]

    return await model_manager.generate(
        prompt=system_prompt,
        persist=False,
        reflect=False
    )

def _sync_call_llm(self, prompt: str, user_intent: str, model_manager: ModelManager) -> str:
    """
    Synchronous bridge for async LLM call.
    Always returns a STRING.
    """

    import asyncio
    import threading

    async def _async_generate():
        result = await model_manager.generate(
            prompt=prompt,
            persist=False,
            reflect=False
        )

        # ✅ Normalize LangChain output
        if hasattr(result, "content"):
            return result.content

        return result

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop
        return asyncio.run(_async_generate())

    # Running loop → offload to thread
    result_container = {}
    error_container = {}

    def _thread_runner():
        try:
            result_container["value"] = asyncio.run(_async_generate())
        except Exception as e:
            error_container["error"] = e

    t = threading.Thread(target=_thread_runner, daemon=True)
    t.start()
    t.join()

    if "error" in error_container:
        raise RuntimeError(
            f"[PipelineTemplateExtractor:{trace_id}] LLM invocation failed"
        ) from error_container["error"]

    return result_container["value"]

# -------------------------------------------------------------------------
# Helper Function
# -------------------------------------------------------------------------
async def hydrate(template: str, variables: Dict[str, Any]) -> str:
    logger.info("Hydrating ...")
    prompt_template = PromptTemplate.from_template(template)
    return prompt_template.invoke(variables).to_string()
