"""
retriever_tool.py
==================
Tool used EXCLUSIVELY by the Product Agent to answer product / catalog /
policy questions via a vector store (RAG).

Guardrails
----------
- This tool only reads from the vector store. It has no side effects,
  so it is safe to retry and safe to call speculatively.
- Input is validated via a Pydantic schema (`RetrieverInput`) so the
  bound LLM cannot pass malformed arguments through to the vector store
  client.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RetrieverInput(BaseModel):
    """Schema for retriever_tool arguments."""

    query: str = Field(..., description="Natural-language product/catalog/policy question.")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve.")


def _get_vectorstore() -> Any:
    """Lazily import and return the configured vector store retriever.

    Deferred import keeps this module importable (e.g. for unit tests)
    even when the vectorstore backend isn't configured yet.
    """
    from src.ingestion.vectorstore import get_retriever  # local import by design

    return get_retriever()


def retrieve_product_context(query: str, top_k: int = 5) -> dict[str, Any]:
    """Retrieve relevant product/catalog/policy context for a user query.

    Parameters
    ----------
    query:
        Natural-language question about products, specs, availability,
        pricing, or store policy.
    top_k:
        Number of top-matching chunks to return.

    Returns
    -------
    dict
        ``{"status": "success", "chunks": [...]}`` on success or
        ``{"status": "error", "error_message": str}`` on failure. The
        tool never raises -- callers (the ReAct loop) always get a
        well-formed dict back.
    """
    try:
        retriever = _get_vectorstore()
        docs = retriever.invoke(query, k=top_k)
        chunks = [
            {"content": d.page_content, "metadata": d.metadata, "source": d.metadata.get("source")}
            for d in docs
        ]
        return {"status": "success", "chunks": chunks, "count": len(chunks)}
    except Exception as exc:  # noqa: BLE001 - tool boundary, must not raise
        logger.exception("retriever_tool failed for query=%r", query)
        return {"status": "error", "error_message": f"Retrieval failed: {exc}"}


retriever_tool = StructuredTool.from_function(
    func=retrieve_product_context,
    name="retriever_tool",
    description=(
        "Search the product catalog / knowledge base for information about "
        "products, specifications, pricing, availability, or store policy. "
        "Use this for ANY factual product question. Does not place orders "
        "or generate recommendations."
    ),
    args_schema=RetrieverInput,
)
