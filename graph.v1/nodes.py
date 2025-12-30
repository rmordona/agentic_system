from orchestrator.decision_engine import is_winner
from orchestrator.voting import majority_vote

def render_history(rounds):
    text = ""
    for i, r in enumerate(rounds, 1):
        text += f"\nROUND {i}\n"
        for a, o in r["outputs"].items():
            text += f"{a.upper()}:\n{o}\n"
    return text.strip()

def agent_node(agent):
    def node(state):
        output = agent.run(
            task=state["task"],
            history=render_history(state["rounds"])
        )
        state["last_outputs"][agent.name] = output
        return state
    return node

#def agent_node(agent):
#    def node(state):
#        out = agent.run(state["task"], render_history(state["rounds"]))
#        state["last_outputs"][agent.name] = out
#        return state
#    return node

def commit_node():
    def node(state):
        state["rounds"].append({"outputs": dict(state["last_outputs"])})
        state["last_outputs"].clear()
        return state
    return node

def synthesizer_decision_node():
    def node(state):
        synth = state["last_outputs"].get("synthesizer")
        if synth and synth["decision"] == "winner":
            state["winner_declared"] = True
        return state
    return node

