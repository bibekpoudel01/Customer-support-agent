"""
recommendation_tool.py
=======================
Tool used EXCLUSIVELY by the Recommendation Agent to generate
personalized product recommendations.

Guardrails
----------
- Read-only against the recommendation service (collaborative filtering
  / embeddings service / rules engine) -- no purchase or cart side effects.
- Bounded `max_results` prevents runaway payloads back into the LLM
  context window.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RecommendationInput(BaseModel):
    """Schema for recommendation_tool arguments."""

    user_id: Optional[str] = Field(
        default=None, description="Customer ID, if known, for personalized recommendations."
    )
    context_query: str = Field(
        ..., description="What the user is shopping for / their stated interest."
    )
    category: Optional[str] = Field(default=None, description="Optional category filter.")
    max_results: int = Field(default=5, ge=1, le=10)


def _get_recommendation_client() -> Any:
    """Lazily import the recommendation service client.

    Replace with your actual recommendation microservice / feature
    store client (e.g. a hosted collaborative-filtering model, a
    vector-similarity index over product embeddings, etc.).
    """
    raise NotImplementedError(
        "Wire this up to your recommendation service (e.g. internal "
        "recsys API, embedding similarity search, or rules engine)."
    )


def get_recommendations(
    context_query: str,
    user_id: Optional[str] = None,
    category: Optional[str] = None,
    max_results: int = 5,
) -> dict[str, Any]:
    """Fetch personalized or contextual product recommendations.

    Parameters
    ----------
    context_query:
        Description of what the user wants recommendations for.
    user_id:
        Known customer ID for personalization; None for anonymous/cold-start.
    category:
        Optional category to constrain results.
    max_results:
        Cap on number of recommended items returned.

    Returns
    -------
    dict
        ``{"status": "success", "items": [...]}`` or
        ``{"status": "error", "error_message": str}``. Never raises.
    """
    try:
        client = _get_recommendation_client()
        items = client.recommend(
            user_id=user_id, query=context_query, category=category, limit=max_results
        )
        return {"status": "success", "items": items, "count": len(items)}
    except NotImplementedError:
        # Explicit, honest failure mode until the real service is wired in --
        # surfaces as a normal tool error to the agent rather than crashing
        # the process, so the graph can degrade gracefully.
        logger.warning("Recommendation client not configured.")
        return {
            "status": "error",
            "error_message": "Recommendation service is not configured yet.",
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("recommendation_tool failed for query=%r", context_query)
        return {"status": "error", "error_message": f"Recommendation failed: {exc}"}


recommendation_tool = StructuredTool.from_function(
    func=get_recommendations,
    name="recommendation_tool",
    description=(
        "Generate personalized or contextual product recommendations based on "
        "customer interest, purchase history, or stated preferences. Use this "
        "ONLY for 'what should I buy / what do you suggest' style requests. "
        "Does not answer factual product questions and does not place orders."
    ),
    args_schema=RecommendationInput,
)
