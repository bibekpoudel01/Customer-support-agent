from langchain.tools import tool
from src.ingestion.vectorstore import (
    get_vectorstore,
    build_vectorstore,
    search,
)

@tool
def reteriver_tool(query:str,session_id:str):
    """
    Search the customer support knowledge base.
    """
    docs = search(query, session_id)
    return "\n\n".join(doc.page_content for doc in docs)

