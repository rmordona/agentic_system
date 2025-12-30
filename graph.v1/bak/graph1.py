from langgraph.graph import StateGraph, END
from graph.state import AgenticState
from graph.nodes import *

def build_graph(optimists, critic, synthesizer):
    g = StateGraph(AgenticState)

    for i, opt in enumerate(optimists):
        g.add_node(f"optimist_{i}", agent_node(opt))

    g.add_node("critic", agent_node(critic))
    g.add_node("synthesizer", agent_node(synthesizer))
    g.add_node("decision", synthesizer_decision_node())
    g.add_node("commit", commit_node())

    for i in range(len(optimists)):
        g.add_edge(f"optimist_{i}", "critic")

    g.add_edge("critic", "synthesizer")
    g.add_edge("synthesizer", "decision")
    g.add_edge("decision", "commit")

    g.add_conditional_edges(
        "commit",
        lambda s: END if s["winner_declared"] else "optimist_0"
    )

    g.set_entry_point("optimist_0")
    return g.compile()

