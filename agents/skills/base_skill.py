# -----------------------------------------------------------------------------
# Project: Agentic System
# File: agents/skills/base_skill.py
#
# Description:
#
#    BaseSkill is the filesystem-driven execution unit for a single agent skill.
#
#    It loads prompts, context definitions, tools, and schemas from the
#    workspace, resolves runtime context, executes the skill, and persists
#    results via MemoryContext.
#
#    BaseSkill does NOT route stages, manage sessions, or select agents.
#    Those concerns belong to the graph and orchestrator layers.
#   
#
# Author: Raymond M.O. Ordona
# Created: 2025-12-31
# Copyright:
#   © 2025 Raymondn Ordona. All rights reserved.
# -----------------------------------------------------------------------------

from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path
from typing import Any, Dict
from langchain_core.prompts import PromptTemplate
from runtime.runtime_context import RuntimeContext
from llm.model_manager import ModelManager
from runtime.tools.tool_client import ToolClient
from events.event_bus import EventBus

from runtime.logger import AgentLogger

class BaseSkill:
    """
    Workspace-scoped, filesystem-driven execution unit.

    Workspace layout:
      workspace/
        stage.json
        agents/
          <skill_name>/
            skill.json
            context.json
            prompt.md
            optional schema.json
    """

    def __init__(
        self,
        workspace_dir: Path,
        skill_name: str,
        runtime_context: RuntimeContext,      # 🔑 expects RuntimeContext
        model_manager: ModelManager,
        tool_client: ToolClient,
        event_bus: EventBus
    ):
        self.workspace_dir = workspace_dir
        self.workspace_name = workspace_dir.name
        self.skill_name = skill_name
        self.skill_dir = workspace_dir / "agents" / skill_name

        self.runtime_context = runtime_context    # 🔑 scoped RuntimeContext
        self.model_manager = model_manager
        self.tool_client = tool_client
        self.event_bus = event_bus

        # --- Load Store Manager
        self.store = self.model_manager.get_store()

        # --- Load artifacts ---
        self.skill_meta = self._load_json("skill.json")
        self.context_meta = self._load_json("context.json")
        self.prompt_template = self._load_prompt("prompt.md")
        self.schema = self._load_optional_json("schema.json")

        # --- Skill metadata ---
        self.role = self.skill_meta["role"]
        self.output_mode = self.skill_meta.get("output_mode", "text")
        self.tools = self.skill_meta.get("tools", [])

        # Bind workspace logger ONCE
        self.logger = AgentLogger.get_logger( component="module", module = __name__ )

    # ------------------------------------------------------------------
    # LangGraph Entry Point
    # ------------------------------------------------------------------

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the skill and returns a LangGraph-compatible state delta.
        """
        self.logger.info(f"Entering next agent run: {state}")
        self.logger.info(f"workspace: {self.workspace_name}")
        self.logger.info(f"Running {self.workspace_name} workspace ...")

        # Bind session and stage to context for this run
        self.logger.info(f"Now binding sessions, stage, task to memory context")
        runtime_context = self.runtime_context \
                .with_session(state["session_id"]) \
                .with_agent(state["agent"]) \
                .with_stage(state["stage"]) \
                .with_task(state["task"]) \
                .generate_key_namespace()

        self.logger.info(f"Entering RAG - Now Resolving context ...")
        context = await self._resolve_context(state, runtime_context)
        self.logger.info(f"Context completed and retrieved: {context}")
 

        self.logger.info(f"Now Rendering prompt with context  ...")
        prompt = self._render_prompt(context)
        self.logger.info(f"Prompt rendered...")

        self.logger.info(f"The System Prompt: {prompt}")

        self.logger.info(f"Now calling LLM Provider with the rendered prompt  ...")
        output = await self._call_llm(prompt, runtime_context, state)
        self.logger.info(f"LLM completed with generated output: {output}")

        if self.schema:
            output = self._validate_schema(output)

        await self._maybe_call_tools(output, state)

        # Send partial update of states
        return self._emit_state_delta(output, state)

    # ------------------------------------------------------------------
    # Context Resolution
    # ------------------------------------------------------------------

    async def _resolve_context(self, state: Dict[str, Any], runtime_context) -> Dict[str, Any]:
        context: Dict[str, Any] = {}

        try:
            for ctx in self.context_meta.get("context", []):
                name = ctx["name"]
                source = ctx["type"]

                if source == "state":
                    context[name] = state.get(ctx.get("key", name))

                elif source == "memory":
                    context[name] = await self._resolve_memory(ctx, runtime_context, state)

                elif source == "text_to_sql":
                    context[name] = await self._resolve_sql(ctx, runtime_context, state)

                elif source == "external":
                    context[name] = await self._resolve_tool(ctx, state)
                    
                elif source == "computed":
                    context[name] = await self._compute_value(ctx, state)

                elif source == "text":
                    context[name] = ctx["text"]

                else:
                    context[name] = None

        except Exception as e:
            self.logger.info(f"Failed to resolve context '{source}'")
            self.logger.error(
                f"Context Metadata being evaluated: '{self.context_meta}': {e}",
                exc_info=True
            )

        return context


    # ------------------------------------------------------------------
    # Memory Resolution
    # ------------------------------------------------------------------

    async def _resolve_memory(self, ctx: dict, runtime_context, state: dict):
        memory_type = ctx.get("memory_type", "semantic")
        filters = ctx.get("filters", {})

        if memory_type == "semantic":
            # context already bound
            return await self.store.query(
                query=state["task"],
                top_k=filters.get("top_k", None),
                limit=filters.get("limit", None),
            )

        if memory_type == "episodic":
            keys=self._memory_key(key_namespace)
            return await self.store.get(
                key=keys,
                top_k=filters.get("top_k", None),
                limit=filters.get("limit", None),
            )

        return None

    async def _compute_value(self, ctx: dict, state: dict) -> Any:
        module_path = ctx["function"]
        module_name, func_name = module_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        fn = getattr(module, func_name)
        return await fn(state) if asyncio.iscoroutinefunction(fn) else fn(state)


    # ------------------------------------------------------------------
    # Text to Sql Resolution
    # ------------------------------------------------------------------

    async def _resolve_sql(self, ctx: dict, runtime_context, state: dict):

        stages = ctx.get("schema", "stages")
        filters = ctx.get("filters", {})

        for stage in stages:
            if stage == "selection":
                pass
            if stage == "extraction":
                pass
            if stage == "execution":
                pass

    # ------------------------------------------------------------------
    # Memory Persistence
    # ------------------------------------------------------------------
    from uuid import uuid4

    def _memory_key(self, key_namespace:tuple):
        uid = str(uuid4())
        keys=dict(key_namespace)
        session_id = keys["session_id"]
        agent      = keys["agent"]
        stage      = keys["stage"]
        namespace  = keys["namespace"]
        return f"{session_id}:{agent}:{stage}:{namespace}:{uid}"


    # ------------------------------------------------------------------
    # Tool Execution (Local Call)
    # ------------------------------------------------------------------

    async def _resolve_tool(self, ctx: dict,  state: dict):
        module_path = ctx["function"]
        module_name, func_name = module_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        fn = getattr(module, func_name)
        return await fn(state) if asyncio.iscoroutinefunction(fn) else fn(state)

    # ------------------------------------------------------------------
    # Tool Call / Tool Invocation (FastMCP)
    # ------------------------------------------------------------------

    async def _maybe_call_tools(self, output: Any, state: dict):
        self.logger.info(f"Tools: {self.tools}")
        for tool in self.tools:
            if tool.get("trigger") == "always":
                await self.tool_client.call(
                    tool_name=tool["name"],
                    params={
                        "workspace": self.workspace_dir.name,
                        "output": output,
                        "state": state,
                    },
                )


    # ------------------------------------------------------------------
    # Prompt & LLM
    # ------------------------------------------------------------------

    def _render_prompt(self, context: Dict[str, Any]) -> str:
        try:
            return PromptTemplate(
                template=self.prompt_template,
                input_variables=list(context.keys()),
            ).format(**context)
        except KeyError as e:
            raise ValueError(
                f"[{self.skill_name}] Missing prompt variable {e}. "
                f"Available context keys: {list(context.keys())}"
            )

    async def _call_llm(self, prompt: str, runtime_context,  state: Dict[str, Any]) -> Any:
        #try:
        return await self.model_manager.generate(
            prompt=prompt,
            namespace=runtime_context.key_namespace, 
            metadata=state,
            )
        #except:
        #    raise NotImplementedError("LLM execution is now handled by memory adapters or external tools.")
        return None

    def _validate_schema(self, output: Any) -> Any:
        return output


    # ------------------------------------------------------------------
    # LangGraph State Delta
    # ------------------------------------------------------------------

    def _emit_state_delta(self, output: Any, state: dict) -> Dict[str, Any]:
        return {
            "history_agents": state.get("history_agents", [])
            + [
                {
                    "stage": state["stage"],
                    "role": self.role,
                    "output": output,
                }
            ],
            "executed_agents_per_stage": {
                **state.get("executed_agents_per_stage", {}),
                state["stage"]: state.get("executed_agents_per_stage", {})
                .get(state["stage"], [])
                + [self.role],
            },
        }

    # ------------------------------------------------------------------
    # File Helpers
    # ------------------------------------------------------------------

    def _load_json(self, name: str) -> dict:
        with open(self.skill_dir / name) as f:
            return json.load(f)

    def _load_optional_json(self, name: str) -> dict | None:
        path = self.skill_dir / name
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None

    def _load_prompt(self, name: str) -> str:
        with open(self.skill_dir / name) as f:
            return f.read()
