from langgraph.graph import StateGraph, START, END
from src.agent.state import State
from src.agent.node.planner import planner_node
from src.agent.node.retriever import retriever_node
from src.agent.node.responder import generate_node
from src.agent.node.sql_lookup import sql_lookup_node

graph = StateGraph(State)

graph.add_node("planner", planner_node)
graph.add_node("retriever", retriever_node)
graph.add_node("sql_lookup", sql_lookup_node)
graph.add_node("generate", generate_node)


def route_planner(state: State) -> str:
    return state.get("intent", "retrieval")  # "conversational" | "sql_lookup" | "retrieval"


graph.add_edge(START, "planner")
graph.add_conditional_edges(
    "planner",
    route_planner,
    {
        "conversational": "generate",
        "sql_lookup": "sql_lookup",
        "retrieval": "retriever",
    },
)
graph.add_edge("retriever", "generate")
graph.add_edge("sql_lookup", "generate")
graph.add_edge("generate", END)


def create_graph(checkpointer):
    return graph.compile(checkpointer=checkpointer)