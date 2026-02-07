from langgraph.graph import StateGraph, END
from typing import TypedDict

from runtime.skill.skill_manager import SkillManager, WorkerAgent
from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")


class AgentState(TypedDict, total=False):
    user_input: str

    # Set by AgentPlanner
    skill_name: str
    skill_instructions: str

    # Set by AgentRunner
    result: str

class AgentRunner:
    """
    Execution node responsible for:
    - Running a SKILL protocol
    - Executing MCP tools
    - Producing a final result
    """

    MAX_TURNS = 10

    def __init__(self, mcp_path: str):
        self.mcp_path = mcp_path
        logger.info("AgentRunner initialized", mcp_path=mcp_path)

    async def __call__(self, state: AgentState) -> AgentState:
        logger.info(
            "AgentRunner starting execution",
            skill=state["selected_skill"],
        )

        messages = state["messages"]

        async with Client("python", [self.mcp_path]) as mcp:
            for turn in range(self.MAX_TURNS):
                logger.debug("Execution turn", turn=turn)

                response = await self.call_llm(messages)

                if not response.get("tool_calls"):
                    logger.info("Execution completed")
                    return {
                        **state,
                        "final_result": response["text"],
                        "completed": True,
                    }

                for call in response["tool_calls"]:
                    logger.info(
                        "Executing tool",
                        tool=call["name"],
                        args=call["args"],
                    )

                    result = await mcp.call_tool(call["name"], call["args"])

                    messages.append(
                        {"role": "assistant", "tool_calls": [call]}
                    )
                    messages.append(
                        {"role": "tool", "content": str(result)}
                    )

        logger.error("Execution exceeded maximum turns")
        raise RuntimeError("Execution limit reached")

    async def call_llm(self, messages: list) -> dict:
        """
        Placeholder LLM execution call.
        Must return:
        - { text: str } OR
        - { tool_calls: [{ name, args }] }
        """
        raise NotImplementedError("LLM execution call not implemented")

class AgentPlanner:
    """
    Planning node responsible for:
    - Injecting discovery manifest
    - Selecting the appropriate skill
    - Activating the SKILL protocol
    """

    def __init__(self, skill_manager: SkillManager):
        self.skill_manager = skill_manager
        logger.info("AgentPlanner initialized")

    async def __call__(self, state: AgentState) -> AgentState:
        logger.info("AgentPlanner invoked")

        system_prompt = self.skill_manager.discovery_prompt()
        user_query = state["user_query"]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ]

        # 🔧 Replace with your real LLM call
        response = await self.call_llm(messages)

        skill_name = response["selected_skill"]
        logger.info("Skill selected", skill=skill_name)

        protocol = self.skill_manager.activate(skill_name)

        return {
            **state,
            "selected_skill": skill_name,
            "skill_protocol": protocol,
            "messages": [
                {"role": "system", "content": protocol},
                {"role": "user", "content": f"START TASK: {user_query}"},
            ],
            "execution_ready": True,
        }

    async def call_llm(self, messages: list) -> dict:
        """
        Placeholder LLM call.
        Must return: { "selected_skill": "<skill-name>" }
        """
        raise NotImplementedError("LLM planning call not implemented")


class CoreEngine:
    """
    Top-level runtime boundary.
    Owns the LangGraph, SkillManager, and execution lifecycle.
    """

    def __init__(self, skills_dir: str, mcp_path: str):
        logger.info("Initializing CoreEngine")

        self.skill_manager = SkillManager(skills_dir)
        self.planner = AgentPlanner(self.skill_manager)
        self.runner = AgentRunner(mcp_path)

        self.graph = self._build_graph()

    def _build_graph(self):
        logger.info("Building LangGraph")

        graph = StateGraph(AgentState)

        graph.add_node("planner", self.planner)
        graph.add_node("runner", self.runner)

        graph.set_entry_point("planner")
        graph.add_edge("planner", "runner")
        graph.add_edge("runner", END)

        return graph.compile()

    async def run(self, user_input: str) -> str:
        logger.info("CoreEngine run invoked", input=user_input)

        final_state = await self.graph.ainvoke({
            "user_query": user_input
        })

        logger.info("CoreEngine run completed")
        return final_state["final_result"]