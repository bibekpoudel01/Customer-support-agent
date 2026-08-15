import logfire
from src.agent.state import AgentState
from src.gateway.client import portkey_client, extract_cache_status
from src.config.config import *



FALLBACK_MESSAGE = "Sorry, I don't have information on that in our catalog."
def format_history(messages: list) -> str:
    lines = []
    for msg in messages[:-1]:
        role_attr = msg.get("role") if isinstance(msg, dict) else getattr(msg, "type", "")
        role = "User" if role_attr in ("human", "user") else "Assistant"
        content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def call_llm(prompt: str) -> tuple[str, str]:
    response = portkey_client.chat.completions.create(
        model=f"@{GROQ_SLUG}/llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": prompt}],
    )
    cache_status = extract_cache_status(response)
    logfire.info(f"Cache status: {cache_status}")
    return response.choices[0].message.content, cache_status


def generate_node(state: AgentState) -> dict:
    intent = state.get("intent", "")
    history_str = format_history(state.get("messages", []))
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else {}
    user_msg = last_msg.get("content", "") if isinstance(last_msg, dict) else getattr(last_msg, "content", "")

    if intent == "conversational":
        logfire.info("Generating conversational response.")
        prompt = f"""You are a friendly e-commerce support assistant.
Answer using ONLY the conversation history below. Do not invent facts.
CONVERSATION HISTORY:
{history_str or "No prior history."}
LATEST USER MESSAGE:
{user_msg}
"""
    elif intent == "sql_lookup":
        logfire.info("Generating SQL-grounded response.")
        product = state.get("sql_result", {})
        prompt = f"""You are an e-commerce support assistant. Answer using ONLY
the product data below. If a detail isn't present in this data, say you
don't have that information — do not guess.

PRODUCT DATA:
{product}

CONVERSATION HISTORY:
{history_str}

LATEST USER MESSAGE:
{user_msg}
"""

    elif intent == "retrieval":
        logfire.info("Generating retrieval-grounded response.")
        max_context_chars = 30000
        full_context = ""
        for doc in state.get("documents", []):
            chunk = f"[product_id={doc.get('product_id')}] {doc.get('content', '')}"
            if len(full_context) + len(chunk) > max_context_chars:
                logfire.warning("Context truncated due to length limits.")
                break
            full_context += chunk + "\n\n"

        prompt = f"""You are an e-commerce support assistant. Answer using ONLY
the product information below. Cite the product_id you used. If the
information isn't present here, say you don't have that information —
do not guess or use outside knowledge.

PRODUCT INFORMATION:
{full_context or "No matching documents."}

CONVERSATION HISTORY:
{history_str}

LATEST USER MESSAGE:
{user_msg}
"""
    
    else:
        logfire.warning(f"Unknown intent '{intent}'. Using fallback response.")
        return {
            "response": FALLBACK_MESSAGE,
            "status": f"Unknown intent '{intent}'. Fallback response used.",
        }

    try:
        llm_response, cache_status = call_llm(prompt)
        is_cached_hit = cache_status == "HIT"
        if is_cached_hit:
            logfire.info("LLM response retrieved from cache.")
            plan_tag = "Response generated from cache."
            status_update = "Answer Generated (cache hit)."
        else:
            logfire.info("LLM response generated fresh.")
            plan_tag = "Response generated from LLM."
            status_update = "Answer Generated (fresh)."
        return {
            "final_answer": llm_response,
            "plan": [plan_tag],
            "status": status_update,
            "messages": [{"role": "assistant", "content": llm_response}],
        }
    except Exception as e:
        logfire.error(f"Error generating response: {e}")
        return {
            "final_answer": FALLBACK_MESSAGE,
            "plan": ["Fallback response used due to error."],
            "status": f"Error during response generation: {e}",
        }
    