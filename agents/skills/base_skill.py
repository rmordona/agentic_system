from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path
from typing import Any, Dict
from fastmcp import Client
from langchain_core.prompts import PromptTemplate
from runtime.logger import AgentLogger

class BaseSkill:
    """
    Workspace-scoped, filesystem-driven execution unit.

    Workspace layout:
      workspace/
        stage.json
        skills/
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
        llm,
        memory_manager,
        embedding_store,
        tool_client: MCPClient,
        event_bus=None,
    ):
        self.workspace_dir = workspace_dir
        self.workspace_name = workspace_dir.name
        self.skill_name = skill_name
        self.skill_dir = workspace_dir / "skills" / skill_name

        self.llm = llm
        self.memory_manager = memory_manager
        self.embedding_store = embedding_store
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
        logger = AgentLogger.get_logger(self.workspace_name, component="base_skill")

    # ------------------------------------------------------------------
    # LangGraph Entry Point
    # ------------------------------------------------------------------

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the skill and returns a LangGraph-compatible state delta.
        """

        context = await self._resolve_context(state)
        prompt = self._render_prompt(context)
        output = await self._call_llm(prompt)

        if self.schema:
            output = self._validate_schema(output)

        await self._maybe_call_tools(output, state)
        await self._persist_memory(output, state)

        return self._emit_state_delta(output, state)

    # ------------------------------------------------------------------
    # Context Resolution
    # ------------------------------------------------------------------

    async def _resolve_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        resolved: Dict[str, Any] = {}

        for ctx in self.context_meta.get("context", []):
            name = ctx["name"]
            source = ctx["type"]

            if source == "state":
                resolved[name] = state.get(ctx.get("key", name))

            elif source == "memory":
                resolved[name] = await self._resolve_memory(ctx, state)

            elif source == "embedding":
                resolved[name] = await self.embedding_store.search(
                    workspace=self.workspace_dir.name,
                    query=state["task"],
                    top_k=ctx.get("top_k", 5),
                )

            elif source == "external":
                resolved[name] = await self.tool_client.call(
                    service=ctx["service"],
                    params=ctx.get("params", {}),
                )

            elif source == "computed":
                resolved[name] = await self._compute_value(ctx, state)

            else:
                resolved[name] = None

        return resolved

    async def _resolve_memory(self, ctx: dict, state: dict):
        memory_type = ctx.get("memory_type", "semantic")
        filters = ctx.get("filters", {})

        if memory_type == "semantic":
            return await self.memory_manager.fetch_semantic(
                workspace=self.workspace_dir.name,
                session_id=state["session_id"],
                task=state["task"],
                top_k=filters.get("top_k", 5),
            )

        if memory_type == "episodic":
            return await self.memory_manager.fetch_episodic(
                workspace=self.workspace_dir.name,
                session_id=state["session_id"],
                stage=state["stage"],
                agent=filters.get("agent"),
                top_k=filters.get("top_k", 3),
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

    async def _call_llm(self, prompt: str) -> Any:
        response = await self.llm.generate(prompt)
        return json.loads(response) if self.output_mode == "json" else response

    def _validate_schema(self, output: Any) -> Any:
        # Optional: jsonschema.validate(...)
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
    # Memory Persistence
    # ------------------------------------------------------------------

    async def _persist_memory(self, output: Any, state: dict):
        await self.memory_manager.store(
            workspace=self.workspace_dir.name,
            session_id=state["session_id"],
            agent=self.role,
            stage=state["stage"],
            output=output,
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

