import logfire
from src.agent.state import AgentState
from src.agent.utils import format_history
from src.gateway.client import get_langchain_llm, extract_cache_status

FALLBACK_MESSAGE = "Sorry, I don't have information on that in our catalog."


def generate_node(state: AgentState) -> dict:
    intent = state.get("intent", "")
    messages = state.get("messages", [])
    history_str = format_history(messages)
    user_msg = messages[-1]["content"] if messages else ""

    if intent == "conversational":
        logfire.info("Generating conversational response.")
        prompt = f"""You're a friendly e-commerce support assistant.
Answer using only the conversation history below — don't invent facts.

History:
{history_str or "No prior history."}

User: {user_msg}
"""

    elif intent == "sql_lookup":
        logfire.info("Generating SQL-grounded response.")
        product = state.get("sql_result", {})
        prompt = f"""You're an e-commerce support assistant. Answer using only the product data below.
If a detail isn't in this data, say you don't have it — don't guess.

Product data:
{product}

History:
{history_str}

User: {user_msg}
"""

    elif intent == "retrieval":
        logfire.info("Generating retrieval-grounded response.")
        max_context_chars = 20000
        full_context = ""
        for doc in state.get("documents", []):
            chunk = f"[product_id={doc.get('product_id')}] {doc.get('content', '')}"
            if len(full_context) + len(chunk) > max_context_chars:
                logfire.warning("Context truncated due to length limits.")
                break
            full_context += chunk + "\n\n"

        prompt = f"""You're an e-commerce support assistant. Answer using only the information below.
Mention the product_id you used. If it's not here, say you don't have that info — don't guess.

Product info:
{full_context or "No matching documents."}

History:
{history_str}

User: {user_msg}
"""

    else:
        logfire.warning(f"Unknown intent '{intent}'. Using fallback response.")
        return {
            "final_answer": FALLBACK_MESSAGE,
            "status": f"Unknown intent '{intent}'. Fallback response used.",
            "messages": [{"role": "assistant", "content": FALLBACK_MESSAGE}],
        }

    try:
        response = get_langchain_llm().invoke([("user", prompt)])
        llm_response = response.content
        cache_status = extract_cache_status(response)
        is_cached_hit = cache_status == "HIT"

        logfire.info("LLM response from cache." if is_cached_hit else "LLM response generated fresh.")
        return {
            "final_answer": llm_response,
            "plan": ["Response generated from cache." if is_cached_hit else "Response generated from LLM."],
            "status": "Answer Generated (cache hit)." if is_cached_hit else "Answer Generated (fresh).",
            "messages": [{"role": "assistant", "content": llm_response}],
        }
    except Exception as e:
        logfire.error(f"Error generating response: {e}")
        return {
            "final_answer": FALLBACK_MESSAGE,
            "plan": ["Fallback response used due to error."],
            "status": f"Error during response generation: {e}",
            "messages": [{"role": "assistant", "content": FALLBACK_MESSAGE}],
        }