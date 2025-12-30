from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastmcp import MCPClient
from langchain.prompts import PromptTemplate


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

    def __init__(
        self,
        skill_dir: Path,
        llm,
        memory_manager,
        embedding_store,
        tool_client: MCPClient,
    ):
        self.skill_dir = skill_dir
        self.llm = llm
        self.memory_manager = memory_manager
        self.embedding_store = embedding_store
        self.tool_client = tool_client

        self.skill = self._load_json("skill.json")
        self.context_spec = self._load_json("context.json")
        self.prompt_template = self._load_prompt("prompt.md")
        self.schema = self._load_optional_json("schema.json")

        self.role = self.skill["role"]
        self.output_mode = self.skill.get("output_mode", "text")
        self.tools = self.skill.get("tools", [])

    # ------------------------------------------------------------------
    # Public Entry Point (used by LangGraph node)
    # ------------------------------------------------------------------

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph entry point.
        Returns state deltas only.
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
        input_context = {}
        for ctx in self.context_meta.get("context", []):
            name = ctx["name"]
            source = ctx["type"]

            if source == "state":
                input_context[name] = state.get(name)

            elif source == "memory":
                memory_type = ctx.get("memory_type", "semantic")
                filters = ctx.get("filters", {})
                if memory_type == "semantic":
                    input_context[name] = await self.memory_manager.fetch_semantic(
                        session_id=state["session_id"],
                        task=state["task"],
                        filters=item.get("filters", {}),
                        top_k=filters.get("top_k", 5)
                    )
                elif memory_type == "episodic":
                    input_context[name] = await self.memory_manager.fetch_episodic(
                        session_id=state["session_id"],
                        agent=item.get("agent"),
                        stage=state["stage"],
                        filters=item.get("filters", {}),
                        top_k=filters.get("top_k", 3)
                    )
            elif source == "embedding":
                resolved[name] = await self.embedding_store.search(
                    query=state["task"],
                    top_k=item.get("top_k", 5),
                )
            elif source == "external":
                service = ctx.get("service")
                namespace = ctx.get("namespace")
                filters = ctx.get("filters", {})
                # FastMCP call
                input_context[name] = await self.fastmcp.call(
                    service=service,
                    params={"namespace": namespace, "top_k": filters.get("top_k", 5)}
                )

            elif source == "computed":
                resolved[name] = await self._compute_value(ctx, state)

            else:
                self.logger.warning(f"Unknown context type: {source} for {name}")
                input_context[name] = None

        return input_context

    # ------------------------------------------
    # Locally and dynamically importing modules
    # ------------------------------------------

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
        return PromptTemplate(
            template=self.prompt_template,
            input_variables=list(context.keys())
        ).format(**context)

    async def _call_llm(self, prompt: str) -> Any:
        response = await self.llm.generate(prompt)

        if self.output_mode == "json":
            return json.loads(response)

        return response

    def _validate_schema(self, output: Any) -> Any:
        # jsonschema.validate(...) could be used here
        return output

    # ------------------------------------------------------------------
    # Tool Invocation (fastmcp)
    # ------------------------------------------------------------------

    async def _maybe_call_tools(self, output: Any, state: dict):
        for tool in self.tools:
            if tool.get("trigger") == "always":
                await self.tool_client.call(
                    tool["name"],
                    {
                        "output": output,
                        "state": state
                    }
                )

    async def _call_tool(self, tool_name: str, params: Dict[str, Any]):
        """
        Placeholder for subclasses to call tools (via FastMCP or other systems).
        """
        if self.tools:
            tool = self.tools.get(tool_name)
            if tool:
                return await tool.call(params)
        return None

    # ------------------------------------------------------------------
    # Memory Persistence
    # ------------------------------------------------------------------

    async def _persist_memory(self, output: Any, state: dict):
        await self.memory_manager.store(
            session_id=state["session_id"],
            agent=self.role,
            stage=state["stage"],
            output=output,
        )

    async def _store_memory(self, *args, **kwargs):
        """
        Placeholder for subclasses to store semantic/episodic memory.
        """
        if self.memory_manager:
            await self.memory_manager.store(*args, **kwargs)

    # ------------------------------------------------------------------
    # LangGraph Delta
    # ------------------------------------------------------------------

    async def _emit(self, event_name: str, payload: Dict[str, Any]):
        """
        Emit events to the event bus if available.
        """
        if self.event_bus:
            await self.event_bus.emit(event_name, payload)


    def _emit_state_delta(self, output: Any, state: dict) -> Dict[str, Any]:
        return {
            "history_agents": [
                {
                    "stage": state["stage"],
                    "role": self.role,
                    "output": output,
                }
            ],
            "executed_agents_per_stage": {
                state["stage"]: [self.role]
            }
        }

    # ------------------------------------------------------------------
    # Helpers
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

