import asyncio
from pathlib import Path
from langgraph.graph import StateGraph, END

# --- 1. SETUP THE INFRASTRUCTURE ---
tool_registry = ToolRegistry() # Scans /tools
artifact_factory = ArtifactFactory()
agent_registry = AgentRegistry() # Loads AGENT.md specs

# --- 2. DEFINE THE AGNOSTIC NODE ---
async def agent_node(state: dict):
    """A generic node that acts based on the current stage."""
    # Hydrate the runner for the current stage
    agent_id = state["current_stage"] 
    runner = agent_registry.get_runner(agent_id, tool_registry)
    
    # The Runner acts on the Control Plane and the Data Plane
    # Returns updated raw strings
    updated_plan, updated_body = await runner.run(
        plan=state["control_raw"],
        body=state["data_raw"]
    )
    
    return {
        "control_raw": updated_plan,
        "data_raw": updated_body,
        "history": state["history"] + [f"executed_{agent_id}"]
    }

# --- 3. THE SMART ROUTER ---
def router(state: dict):
    # Use the Factory to see what's left to do
    plan_dict = artifact_factory.to_dict(state["control_raw"])
    
    # Find the next non-superseded task
    next_task = next((t for t in plan_dict['current_plan'] if not t['superseded']), None)
    
    if not next_task:
        return END  # The "__end__" signal
    
    # Transition to the next stage defined in the Markdown
    return next_task['stage']

# --- 4. BUILD THE GRAPH ---
workflow = StateGraph(dict) # Our Agnostic State
workflow.add_node("process_work", agent_node)
workflow.set_entry_point("process_work")

# After processing, ask the router where to go next
workflow.add_conditional_edges("process_work", router)

app = workflow.compile()

# --- 5. EXECUTION ---
async def main():
    # Initial "Entry Ticket"
    initial_state = {
        "control_raw": Path("plan.md").read_text(),
        "data_raw": Path("logic.py").read_text(),
        "history": []
    }

    async for event in app.astream(initial_state):
        for node_name, state_update in event.items():
            print(f"[{node_name}] Activity detected...")
            
    # Once the loop ends naturally via END
    print("Workflow complete. Saving artifacts...")
    # Final state is available here to write back to disk
    
if __name__ == "__main__":
    asyncio.run(main())
