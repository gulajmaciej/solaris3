"""Graph builder for crew officer."""

# Per langgraph-Application structure.md: Graphs

from langgraph.graph import END, StateGraph

from agents.crew_officer.nodes import (
    apply_tool,
    decide_tool,
    fuse,
    observe_stub,
    read_memory,
    route_phase,
    route_phase_node,
    sense_world,
    write_memory,
)
from agents.crew_officer.state import CrewOfficerState


def build_graph() -> StateGraph:
    # Per langgraph-Application structure.md: Graphs
    graph = StateGraph(CrewOfficerState)
    graph.add_node("route_phase", route_phase_node)
    graph.add_node("read_memory", read_memory)
    graph.add_node("sense_world", sense_world)
    graph.add_node("fuse", fuse)
    graph.add_node("decide_tool", decide_tool)
    graph.add_node("apply_tool", apply_tool)
    graph.add_node("write_memory", write_memory)
    graph.add_node("observe_stub", observe_stub)

    graph.set_entry_point("route_phase")
    graph.add_conditional_edges("route_phase", route_phase, {"read_memory": "read_memory", "observe_stub": "observe_stub"})
    graph.add_edge("read_memory", "sense_world")
    graph.add_edge("sense_world", "fuse")
    graph.add_edge("fuse", "decide_tool")
    graph.add_edge("decide_tool", "apply_tool")
    graph.add_edge("apply_tool", "write_memory")
    graph.add_edge("write_memory", END)
    graph.add_edge("observe_stub", END)
    return graph
