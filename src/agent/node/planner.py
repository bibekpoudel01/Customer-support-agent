from typing import Literal
from pydantic import BaseModel, Field
import logfire
from src.agent.state import State
from src.gateway.client import get_langchain_llm

llm = get_langchain_llm(feature="planner")


class RouteDecision(BaseModel):
    intent: Literal["conversational", "sql_lookup", "retrieval"] = Field(
        ..., description=("conversational: greeting, small talk, or answerable purely from conversation history (e.g. 'what did I just ask'). "
            "sql_lookup: needs LIVE structured data — stock/availability, price,order status, product specs for a SPECIFIC named product. "
            "retrieval: needs STATIC document content — return policy, FAQs, shipping info, general product descriptions, warranty terms.")
)
    search_query: str = Field(..., description=("Self-contained query rewritten from context. Empty string if intent is 'conversational'. Include the specific product name if intent is 'sql_lookup' (e.g. 'WiFi Smart Plug availability')."))

def format_history(messages: list) -> str:
    lines = []
    for msg in messages[:-1]:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def planner_node(state: State) -> dict:
    """Classifies the latest turn and rewrites it into a self-contained query."""
    history = format_history(state["messages"])
    user_message = state["messages"][-1]["content"] if state["messages"] else ""

    prompt = f"""E-commerce support agent router. Given the conversation, classify
the latest message and rewrite it as a self-contained query .

History:
{history}

Latest: "{user_message}"

Examples:
"hi" -> conversational
"is the WiFi Smart Plug in stock?" -> sql_lookup, "WiFi Smart Plug availability"
"what's your return policy?" -> retrieval, "return policy"
"""

    with logfire.span("🧠 Planner decision"):
        router = llm.with_structured_output(RouteDecision)
        decision = router.invoke(prompt)
        logfire.info(f"Intent: {decision.intent} | Query: {decision.search_query}")

    if decision.intent == "conversational":
        return {
            "current_query": "CONVERSATIONAL",
            "intent": "conversational",
            "status": "Handling conversationally (using memory)...",
            "plan": ["Intent: Conversational/Memory", "Retrieval: Skipped"],
        }
    elif decision.intent == "sql_lookup":
        return {
            "current_query": "sql_lookup",
            "intent": "sql_lookup",
            "status": f"Intent: SQL lookup. Query: {decision.search_query}",
            "plan": [f"Intent: SQL Lookup", f"Search term: {decision.search_query}"],
        }

    else:  # retrieval
        return {
            "current_query": decision.search_query,
            "intent": "retrieval",
            "status": f"Intent: Retrieval. Query: {decision.search_query}",
            "plan": [f"Intent: Retrieval", f"Search term: {decision.search_query}"],
        }



