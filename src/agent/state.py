from typing import Annotated, NotRequired, TypedDict
import operator


class AgentMessage(TypedDict):
    role: str
    content: str


class AgentState(TypedDict, total=False):
    """Shared state across planner/retriever/sql/responder nodes."""
    session_id: str
    messages: Annotated[list[AgentMessage], operator.add]
    intent: str
    route: str
    
    current_query: str
    status: str
    final_answer: str
    plan: list[str]
    documents: list[dict]
    sql_result: dict


State = AgentState
