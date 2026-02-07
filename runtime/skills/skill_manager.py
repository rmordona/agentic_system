"""
SKILL-BASED AGENT ORCHESTRATION FRAMEWORK
========================================

This module implements a production-grade, skill-driven agent architecture
designed to execute deterministic procedural runbooks (SKILL.md files)
using Large Language Models (LLMs) and a tool execution backend (FastMCP).

ARCHITECTURE OVERVIEW
---------------------
The system is organized into four primary agent roles:

1. SkillManager
   - Discovers and indexes available SKILL.md files
   - Exposes a lightweight discovery manifest to the LLM
   - Activates a skill by loading its full execution protocol

2. SkillAgentOrchestrator
   - Acts as the primary interaction loop with the LLM
   - Handles skill selection, activation, and tool-mediated execution
   - Maintains bounded execution to prevent infinite reasoning loops

3. WorkerAgent
   - A focused, stateless execution agent
   - Executes a single SKILL.md runbook in isolation
   - Interacts with tools via an MCP client and returns a final result

4. SupervisorAgent
   - High-level coordinator responsible for delegation
   - Selects the appropriate skill
   - Spawns a WorkerAgent and receives only the final output

DESIGN PRINCIPLES
-----------------
- SKILL.md files are treated as authoritative, executable protocols
- LLMs are constrained planners, not autonomous decision-makers
- Tool access is mediated exclusively through MCP
- Context isolation is enforced between supervisor and worker agents
- Execution is deterministic, bounded, and auditable

This module intentionally separates discovery, orchestration, execution,
and supervision to support scalable multi-skill agent systems.

Dependencies:
- fastmcp.Client for tool execution
- YAML frontmatter for skill metadata discovery
- Async execution model (asyncio-compatible)

This file contains no application entrypoint and is intended to be imported
and integrated into a larger agent runtime or service.
"""

import os
import yaml
import asyncio
from typing import Dict, List, Optional
from fastmcp import Client

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")


class SkillManager:
    """
    SkillManager is responsible for discovering, indexing, and activating
    procedural skills defined as SKILL.md files on disk.

    Responsibilities:
    -----------------
    - Perform lightweight discovery by scanning only YAML frontmatter
    - Maintain an in-memory registry of available skills
    - Provide a concise discovery manifest suitable for LLM system prompts
    - Load and return the full SKILL protocol on activation

    Design Notes:
    -------------
    - Discovery is intentionally shallow to minimize I/O and context size
    - Full SKILL bodies are loaded only when explicitly activated
    - The manager is agnostic to execution semantics and tooling

    This class represents the boundary between static skill definitions
    and dynamic agent execution.
    """

    def __init__(self, skills_dir: str):
        self.skills_dir = skills_dir
        self.registry: Dict[str, dict] = {}
        logger.info("Initializing SkillManager", skills_dir=skills_dir)
        self._load_inventory()

    def _load_inventory(self):
        """Level 1: Discovery. Scans only the YAML headers."""
        logger.info("Starting skill discovery", directory=self.skills_dir)

        try:
            for skill_folder in os.listdir(self.skills_dir):
                skill_path = os.path.join(self.skills_dir, skill_folder, "SKILL.md")
                logger.debug("Scanning skill folder", folder=skill_folder)

                if os.path.exists(skill_path):
                    logger.debug("Found SKILL.md", path=skill_path)

                    with open(skill_path, 'r') as f:
                        content = f.read()

                    if content.startswith('---'):
                        _, frontmatter, body = content.split('---', 2)
                        metadata = yaml.safe_load(frontmatter)

                        self.registry[metadata['name']] = {
                            "description": metadata['description'],
                            "body": body.strip(),
                            "path": os.path.dirname(skill_path),
                            "allowed_tools": metadata.get('allowed-tools', [])
                        }

                        logger.info(
                            "Registered skill",
                            skill=metadata['name'],
                            allowed_tools=metadata.get('allowed-tools', [])
                        )
                    else:
                        logger.warning(
                            "SKILL.md missing YAML frontmatter",
                            path=skill_path
                        )
        except Exception as e:
            logger.exception("Failed during skill discovery")
            raise

        logger.info(
            "Skill discovery complete",
            total_skills=len(self.registry)
        )

    def get_discovery_prompt(self) -> str:
        """
        Constructs a compact, human- and LLM-readable manifest of available skills.

        This prompt is intended to be injected into the system context and serves
        as a 'library card catalog' that enables the model to select the correct
        skill without loading full protocols.

        Returns:
        --------
        str
            A formatted list of skill names and descriptions with activation
            instructions.
        """
        logger.debug("Generating discovery prompt")

        manifest = "AVAILABLE SKILLS:\n"
        for name, data in self.registry.items():
            manifest += f"- {name}: {data['description']}\n"

        manifest += "\nTo use a skill, call the 'activate_skill(name)' tool."
        return manifest

    def activate_skill(self, name: str) -> str:
        """
        Activates a skill by returning its full SKILL.md body.

        This method represents Level 2 loading, where the complete procedural
        protocol is injected into the LLM context and treated as executable
        instructions.

        Parameters:
        -----------
        name : str
            The registered name of the skill to activate.

        Returns:
        --------
        str
            The full SKILL.md body, or an error message if not found.
        """
        logger.info("Activating skill", skill=name)

        skill = self.registry.get(name)
        if not skill:
            logger.error("Requested skill not found", skill=name)
            return "Error: Skill not found."

        logger.debug(
            "Skill activated",
            skill=name,
            path=skill["path"]
        )
        return skill["body"]


class SkillAgentOrchestrator:
    """
    SkillAgentOrchestrator manages the main interaction loop between the user,
    the LLM, and the tool execution backend.

    Responsibilities:
    -----------------
    - Inject the discovery manifest into the system prompt
    - Allow the LLM to select and activate a skill
    - Execute tool calls via MCP as directed by the active SKILL
    - Enforce a bounded reasoning loop to prevent runaway execution

    Design Notes:
    -------------
    - This orchestrator does not execute skills itself; it mediates execution
    - Skill logic lives entirely inside SKILL.md and the LLM's interpretation
    - The orchestrator remains stateless across requests
    """

    def __init__(self, manager: SkillManager, mcp_path: str):
        self.manager = manager
        self.mcp_path = mcp_path
        logger.info(
            "SkillAgentOrchestrator initialized",
            mcp_path=mcp_path
        )

    async def handle_request(self, user_query: str):
        logger.info("Handling user request", query=user_query)

        async with Client("python", [self.mcp_path]) as mcp:
            logger.info("MCP client started", mcp_path=self.mcp_path)

            messages = [
                {"role": "system", "content": self.manager.get_discovery_prompt()},
                {"role": "user", "content": user_query}
            ]

            for step in range(15):
                logger.debug("LLM execution step", step=step)

                response = await self.call_llm(messages)

                if response.tool_call and response.tool_name == "activate_skill":
                    skill_name = response.tool_args['name']
                    logger.info("LLM requested skill activation", skill=skill_name)

                    skill_body = self.manager.activate_skill(skill_name)
                    messages.append({
                        "role": "developer",
                        "content": f"PROTOCOL LOADED:\n{skill_body}"
                    })
                    continue

                if response.tool_calls:
                    for call in response.tool_calls:
                        logger.info(
                            "Executing MCP tool",
                            tool=call.name,
                            args=call.args
                        )

                        observation = await mcp.call_tool(call.name, call.args)
                        messages.append({"role": "tool", "content": str(observation)})
                else:
                    logger.info("Task completed by orchestrator")
                    return response.text

        logger.warning("Execution loop exited without completion")
        return None


class WorkerAgent:
    """
    WorkerAgent is a focused, stateless execution unit responsible for running
    a single SKILL.md protocol to completion.

    Responsibilities:
    -----------------
    - Execute a single procedural runbook in isolation
    - Interact with tools via MCP as instructed by the SKILL
    - Maintain its own short-lived execution history
    - Terminate when the SKILL indicates completion

    Design Notes:
    -------------
    - WorkerAgents are disposable and context-isolated
    - They do not perform skill discovery or selection
    - All authority comes from the injected SKILL instructions
    """

    def __init__(self, name, instructions, mcp_client):
        self.name = name
        self.instructions = instructions
        self.mcp = mcp_client
        self.history = [{"role": "system", "content": instructions}]

        logger.info(
            "WorkerAgent spawned",
            skill=name
        )

    async def execute(self, task_description: str):
        logger.info(
            "Worker execution started",
            skill=self.name,
            task=task_description
        )

        self.history.append({
            "role": "user",
            "content": f"START TASK: {task_description}"
        })

        for turn in range(10):
            logger.debug(
                "Worker reasoning turn",
                skill=self.name,
                turn=turn
            )

            response = await self.get_llm_response(self.history)

            if not response.tool_calls:
                logger.info(
                    "Worker completed execution",
                    skill=self.name
                )
                return response.text

            for call in response.tool_calls:
                logger.info(
                    "Worker executing tool",
                    skill=self.name,
                    tool=call.name,
                    args=call.args
                )

                result = await self.mcp.call_tool(call.name, call.args)

                self.history.append({"role": "assistant", "tool_calls": [call]})
                self.history.append({"role": "tool", "content": str(result)})

        logger.warning(
            "Worker reached max turns without completion",
            skill=self.name
        )
        return "Error: Worker execution limit reached."


class SupervisorAgent:
    """
    SupervisorAgent is the top-level coordinator responsible for delegating
    user requests to the appropriate skill and managing execution boundaries.

    Responsibilities:
    -----------------
    - Initialize and own the SkillManager
    - Select the appropriate skill for a given request
    - Spawn a WorkerAgent with the full SKILL protocol
    - Receive and return only the final summarized output

    Design Notes:
    -------------
    - The supervisor maintains a clean, minimal context
    - It does not observe intermediate tool calls or reasoning
    - This
    """

    def __init__(self, skills_dir, mcp_script):
        logger.info("Initializing SupervisorAgent")

        self.manager = SkillManager(skills_dir)
        self.mcp_script = mcp_script

    async def run(self, user_input: str):
        logger.info("Supervisor received request", input=user_input)

        async with Client("python", [self.mcp_script]) as mcp:
            logger.info("Supervisor MCP client started")

            skill_to_use = "automated-pr-reviewer"
            logger.info(
                "Supervisor selected skill",
                skill=skill_to_use
            )

            instructions = self.manager.activate_skill(skill_to_use)
            worker = WorkerAgent(skill_to_use, instructions, mcp)

            logger.info(
                "Delegating task to worker",
                skill=skill_to_use
            )

            final_report = await worker.execute(user_input)

            logger.info(
                "Supervisor received final report",
                skill=skill_to_use
            )

            return f"Review Complete. Here is the summary: {final_report}"
