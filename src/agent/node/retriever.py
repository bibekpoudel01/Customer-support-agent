from src.agent.state import AgentState
from src.ingestion.vectorstore import search

GLOBAL_DOCS_SESSION = "default_user"  # must match session_id used in _run_ingestion()

def retriever_node(state: AgentState) -> dict:
    """Retrieves grounded context for the current query."""
    current_query = state.get("current_query", "")

    if current_query == "CONVERSATIONAL":
        return {
            "documents": [],
            "status": "Skipped retrieval (conversational intent)",
        }

    try:
        results = search(session_id=GLOBAL_DOCS_SESSION, query=current_query)
    except Exception as e:
        return {
            "documents": [],
            "status": f"Error during retrieval: {e}",
        }

    documents = [
        {"content": doc.page_content, "product_id": doc.metadata.get("product_id"),
         "title": doc.metadata.get("title")}
        for doc in results
    ]

    return {
        "documents": documents,
        "status": f"Retrieved {len(documents)} documents",
        "plan": [f"Intent: {state.get('intent', 'unknown')}", f"Search term: {current_query}"],
    }