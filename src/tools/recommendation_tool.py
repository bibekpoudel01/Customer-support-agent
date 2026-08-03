from langchain_core.tools import tool

from src.ingestion.vectorstore import search


@tool
def recommendation_tool(requirements: str, session_id: str) -> str:
    """Retrieve products matching the user's requirements."""
    docs = search(query=requirements, session_id=session_id)
    if not docs:
        return "No matching products found."
    return "\n\n".join(doc.page_content for doc in docs)