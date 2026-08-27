from typing import Literal
from pydantic import BaseModel, Field
import logfire
from src.agent.state import State
from src.gateway.client import get_langchain_llm

llm = get_langchain_llm(feature="planner")

class RouteDecision(BaseModel):
    intent: Literal["conversational", "sql_lookup", "retrieval"] 

def format_history(messages: list) -> str:
    lines = []
    for msg in messages[:-1]:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def planner_node(state: State) -> dict:
    """Plan to choose which route to take based on the current query."""
    history = format_history(state["messages"])
    user_message = state["messages"][-1]["content"] if state["messages"] else ""

    prompt = f"""You are a planner for a customer support agent.
Based on the conversation history:
{history}
And the latest user message: "{user_message}"
Decide the intent of the user.
Follow the rules to choose or path to select what what sepcific path consist of :
1. Use CONVERSATIONAL if user is asking about general question that can answer from conversation{conversation}
2. Use SQL_LOOKUP if user is asking about Product PRICE, Stautus,ORDER (Dynamic answer that can be changes frequently)
3. Use RETRIEVER if user is asking about ptoduct content lie product description ,
policy,or any information that never changes frequently
"""

    with logfire.span("Planner decision"):
        router = llm.with_structured_output(
            RouteDecision,
            method="function_calling"
        )
        decision = router.invoke(prompt)
        logfire.info(f"Intent: {decision.intent} | Query: {decision.search_query}")

    if decision.intent == "conversational":
        return {
            "current_query": "CONVERSATIONAL",
            "intent": "conversational",
            "status": "Handling conversationally (using memory)...",
            "plan": ["Intent: Conversational/Memory", "Retrieval: Skipped","SQL Lookup: Skipped"],
        }
    elif decision.intent == "sql_lookup":
        return {
            "current_query": "sql_lookup",
            "intent": "sql_lookup",
            "status": f"Intent: SQL lookup. Query: {decision.search_query}",
            "plan": [f"Intent: SQL Lookup", f"Search term: {decision.search_query}"],
        }

    else:
        return {
            "current_query": decision.search_query,
            "intent": "retrieval",
            "status": f"Intent: Retrieval. Query: {decision.search_query}",
            "plan": [f"Intent: Retrieval", f"Search term: {decision.search_query}"],
        }