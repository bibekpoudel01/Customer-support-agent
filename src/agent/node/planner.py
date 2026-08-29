from typing import Literal, Optional
from pydantic import BaseModel, Field
import logfire
from src.agent.state import State
from src.agent.utils import format_history
from src.gateway.client import get_langchain_llm

llm = get_langchain_llm(feature="planner")


print("PLANNER LLM:", llm)

class RouteDecision(BaseModel):
    intent: Literal["conversational", "sql_lookup", "retrieval"]
    search_query: Optional[str] = Field(
        None, description="The core thing the user is asking about, in a few words."
    )


PLANNER_PROMPT = """You are the planner for an e-commerce support agent.

Conversation so far:
{history}

Latest user message: "{user_message}"

Pick exactly one path:
- conversational: greetings, small talk, or something already answered above
- sql_lookup: price, stock, or order status — anything that can change right now
- retrieval: product descriptions, policies, or other info that stays the same

If the path is sql_lookup or retrieval, also give a short search_query naming what the user wants.
"""


def planner_node(state: State) -> dict:
    """Decides which node handles the current turn."""
    messages = state.get("messages", [])
    history = format_history(messages)
    user_message = messages[-1]["content"] if messages else ""

    prompt = PLANNER_PROMPT.format(history=history or "No prior history.", user_message=user_message)

    with logfire.span("Planner decision"):
        router = llm.with_structured_output(RouteDecision, method="function_calling")
        decision = router.invoke(prompt)
        logfire.info(f"Intent: {decision.intent} | Query: {decision.search_query}")

    if decision.intent == "conversational":
        return {
            "current_query": "CONVERSATIONAL",
            "intent": "conversational",
            "status": "Handling conversationally (using memory)...",
            "plan": ["Intent: Conversational/Memory", "Retrieval: Skipped", "SQL Lookup: Skipped"],
        }
    elif decision.intent == "sql_lookup":
        return {
            "current_query": decision.search_query or user_message,
            "intent": "sql_lookup",
            "status": f"Intent: SQL lookup. Query: {decision.search_query}",
            "plan": ["Intent: SQL Lookup", f"Search term: {decision.search_query}"],
        }
    else:
        return {
            "current_query": decision.search_query or user_message,
            "intent": "retrieval",
            "status": f"Intent: Retrieval. Query: {decision.search_query}",
            "plan": ["Intent: Retrieval", f"Search term: {decision.search_query}"],
        }