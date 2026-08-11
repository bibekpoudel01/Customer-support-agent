from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from src.agent.state import State
from src.agent.node.planner import planner_node
from src.agent.node.retriever import retriever_node
from src.agent.node.responder import generate_node
from src.agent.node.sql_lookup import sql_lookup_node
from src.services.database_services import get_db_pool

graph = StateGraph(State)
graph.add_node("planner", planner_node)
graph.add_node("retriever", retriever_node)
graph.add_node("sql_lookup", sql_lookup_node)
graph.add_node("generate", generate_node)


def route_Planner(state: State) -> str:
    """Routing function receives the FULL state, not a single field.
    Must return one of the path_map keys below (strings), never a
    node function reference."""
    current_query = state.get("current_query", "")
    if current_query == "CONVERSATIONAL":
        return "CONVERSATIONAL"
    elif current_query == "sql_lookup":
        return "sql_lookup"
    else:
        return "retriever"


graph.add_edge(START, "planner")
graph.add_conditional_edges(
    "planner",
    route_Planner,
    {"CONVERSATIONAL": "generate", "sql_lookup": "sql_lookup", "retriever": "retriever"},
)
graph.add_edge("retriever", "generate")
graph.add_edge("sql_lookup", "generate")
graph.add_edge("generate", END)


def checkpointer():
    db_pool = get_db_pool()
    if not db_pool:
        return MemorySaver()
    return PostgresSaver(db_pool, table_name="agent_state")


# Keep a reference to the compiled app — previously this was discarded,
# so nothing could actually import/run the graph.
app = graph.compile(checkpointer=checkpointer())