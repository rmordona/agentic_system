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
from runtime.tools.client import ToolClient
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

    # Inherit the logger

    def __init__(
        self,
        workspace_dir: Path,
        skill_name: str,
        runtime_context: RuntimeContext,      # 🔑 expects RuntimeContext
        model_manager: ModelManager,
        tool_client: ToolClient,
        event_bus=None,
    ):
        self.workspace_dir = workspace_dir
        self.workspace_name = workspace_dir.name
        self.skill_name = skill_name
        self.skill_dir = workspace_dir / "agents" / skill_name

        self.runtime_context = runtime_context    # 🔑 scoped RuntimeContext
        self.model_manager = model_manager
        self.tool_client = tool_client
        self.event_bus = event_bus

        # --- Load artifacts ---
        self.skill_meta = self._load_json("skill.json")
        self.context_meta = self._load_json("context.json")
        self.prompt_template = self._load_prompt("prompt.md")
        self.schema = self._load_optional_json("schema.json")

        # --- Skill metadata ---
        self.role = self.skill_meta["role"]
        self.output_mode = self.skill_meta.get("output_mode", "text")
        self.tools = self.skill_meta.get("tools", [])

        # 🔑 Bind workspace logger ONCE
        global logger
        logger = AgentLogger.get_logger(self.workspace_name, component="runtime")

    # ------------------------------------------------------------------
    # LangGraph Entry Point
    # ------------------------------------------------------------------

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the skill and returns a LangGraph-compatible state delta.
        """
        print(f"Entering next agent run: {state}")
        print(f"workspace: {self.workspace_name}")
        logger.info(f"Running {self.workspace_name} workspace ...")

        # Bind session and stage to context for this run
        logger.info(f"Now binding sessions, stage, task to memory context")
        runtime_context = self.runtime_context.with_session(state["session_id"]).with_stage(state["stage"]).with_task(state["task"]).generate_key_namespace()

        logger.info(f"Now Resolving context ...")
        context = await self._resolve_context(state, runtime_context)
        logger.info(f"Context completed and retrieved: {context}")
 

        logger.info(f"Now Rendering prompt with context  ...")
        prompt = self._render_prompt(context)
        logger.info(f"Prompt rendered...")
        logger.info(f"The System Prompt: {prompt}")

        logger.info(f"Now calling llm with the rendered prompt  ...")
        output = await self._call_llm(prompt, state)
        logger.info(f"LLM completed with generated output: {output}")

        if self.schema:
            output = self._validate_schema(output)

        await self._maybe_call_tools(output, state)
        await self._persist_memory(output, runtime_context)

        return self._emit_state_delta(output, state)

    # ------------------------------------------------------------------
    # Context Resolution
    # ------------------------------------------------------------------

    async def _resolve_context(self, state: Dict[str, Any], runtime_context) -> Dict[str, Any]:
        resolved: Dict[str, Any] = {}

        try:
            for ctx in self.context_meta.get("context", []):
                name = ctx["name"]
                source = ctx["type"]

                if source == "state":
                    resolved[name] = state.get(ctx.get("key", name))

                elif source == "memory":
                    resolved[name] = await self._resolve_memory(ctx, runtime_context, state)

                elif source == "embedding":
                    resolved[name] = await runtime_context.semantic_search(
                        query=state["task"],
                        top_k=ctx.get("top_k", 5),
                        filters=ctx.get("filters", None)
                    )
                elif source == "nl2sql":
                    resolved[name] = await runtime_context.query(
                        query=state["task"],
                        top_k=ctx.get("top_k", 5),
                        filters=ctx.get("filters", None)
                    )
                elif source == "external":
                    resolved[name] = await self.tool_client.call(
                        tool_name=ctx["service"],
                        params=ctx.get("params", {}),
                    )
                elif source == "computed":
                    resolved[name] = await self._compute_value(ctx, state)
                elif source == "text":
                    resolved[name] = ctx["text"]
                else:
                    resolved[name] = None

        except Exception as e:
            logger.info(f"Failed to resolve context '{source}'")
            logger.error(
                f"Context Metadata being evaluated: '{self.context_meta}': {e}",
                exc_info=True
            )

        return resolved

    # ------------------------------------------------------------------
    # Memory Persistence
    # ------------------------------------------------------------------
    from uuid import uuid4

    def _memory_key(self, key_namespace:tuple):
        uid = str(uuid4())
        keys=dict(key_namespace)
        session_id = keys["session_id"]
        agent      = keys["agent"]
        stage      = keys["agent"]
        namespace  = keys["namespace"]
        return f"{session_id}:{agent}:{stage}:{namespace}:{uid}"

    async def _persist_memory(self, output: Any, runtime_context):
        await runtime_context.store(memory=output)

    # ------------------------------------------------------------------
    # Memory Resolution
    # ------------------------------------------------------------------

    async def _resolve_memory(self, ctx: dict, runtime_context, state: dict):
        memory_type = ctx.get("memory_type", "semantic")
        filters = ctx.get("filters", {})

        if memory_type == "semantic":
            # context already bound
            return await runtime_context.query(
                query=state["task"],
                top_k=filters.get("top_k", None),
                limit=filters.get("limit", None),
            )

        if memory_type == "episodic":
            return await runtime_context.fetch_memory(
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

    async def _call_llm(self, prompt: str, state: Dict[str, Any]) -> Any:
        #try:
        return await self.model_manager.generate(
            prompt=prompt,
            inputs=state,
            memory_key=state.get("session_id")
            )
        #except:
        #    raise NotImplementedError("LLM execution is now handled by memory adapters or external tools.")
        return None

    def _validate_schema(self, output: Any) -> Any:
        return output

    # ------------------------------------------------------------------
    # Tool Invocation (FastMCP)
    # ------------------------------------------------------------------

    async def _maybe_call_tools(self, output: Any, state: dict):
        for tool in self.tools:
            if tool.get("trigger") == "always":
                await self.tool_client.call(
                    service=tool["name"],
                    params={
                        "workspace": self.workspace_dir.name,
                        "output": output,
                        "state": state,
                    },
                )



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
