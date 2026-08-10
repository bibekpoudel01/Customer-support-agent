"""
search_tool.py
===============
Web search tool used as a FALLBACK by the Product Agent when the
internal catalog/knowledge-base retriever (`retriever_tool`) doesn't
surface an answer.

Why this exists
----------------
The Product Agent's primary source of truth is the internal vector
store (accurate pricing, live availability, exact policy text). But
customers also ask things that legitimately live outside that KB --
e.g. "does this laptop support Thunderbolt 4", manufacturer recall
notices, general spec questions about a product that hasn't been fully
ingested yet. Rather than let the LLM guess from parametric memory,
this tool lets the Product Agent ground those answers in a live web
search instead.

Guardrails
----------
- This is a SECONDARY tool. The Product Agent's system prompt (see
  product.py) instructs it to always try `retriever_tool` first and
  only fall back to `search_tool` when the catalog has no answer.
- Web results NEVER override catalog data for price, availability, or
  order-relevant policy -- those must come from the internal catalog,
  since it's the authoritative, current source. This tool is for
  general/manufacturer-level factual info only, and the system prompt
  enforces that split.
- Domain allow/deny-listing is supported so you can keep results to
  trusted domains (manufacturer sites, reputable review outlets) and
  keep competitor storefronts / low-quality SEO content out of
  customer-facing answers.
- Every result includes its source URL so answers remain citable, and
  the tool truncates snippet length to avoid pulling large blocks of
  copyrighted text into the agent's context.
- Never raises: all failures return a structured error dict.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_MAX_SNIPPET_CHARS = 500
_DEFAULT_ALLOWED_DOMAINS: Optional[list[str]] = None  # e.g. ["apple.com", "reviews.com"]
_DEFAULT_BLOCKED_DOMAINS: list[str] = []  # e.g. competitor storefronts


class SearchToolInput(BaseModel):
    """Schema for search_tool arguments."""

    query: str = Field(
        ..., description="Specific factual product question to search the web for."
    )
    max_results: int = Field(default=5, ge=1, le=10)


def _get_search_client() -> Any:
    """Lazily import and return the configured web search client.

    Replace with your actual provider, e.g.:
        from langchain_community.tools.tavily_search import TavilySearchResults
        return TavilySearchResults(max_results=5)
    or wire directly to the Anthropic web_search tool via the API, or to
    a Google/Bing Custom Search client.
    """
    raise NotImplementedError(
        "Wire this up to your web search provider (Tavily, Google CSE, Bing, etc.)."
    )


def _domain_allowed(url: str, allowed: Optional[list[str]], blocked: list[str]) -> bool:
    """Check a result URL against allow/block lists.

    An empty `allowed` list means "no allow-list restriction" (only
    `blocked` is enforced). This keeps the default permissive but gives
    ops teams a lever to lock results down to trusted domains.
    """
    lowered = url.lower()
    if any(domain.lower() in lowered for domain in blocked):
        return False
    if allowed and not any(domain.lower() in lowered for domain in allowed):
        return False
    return True


def search_web_for_product_info(
    query: str,
    max_results: int = 5,
    allowed_domains: Optional[list[str]] = None,
    blocked_domains: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Search the public web for product/manufacturer information.

    Use ONLY as a fallback when the internal catalog retriever has no
    answer. Never use this for order status, recommendations, pricing,
    or availability -- those must come from internal systems.

    Parameters
    ----------
    query:
        Specific, narrow factual question (avoid broad/ambiguous queries).
    max_results:
        Cap on number of results returned.
    allowed_domains:
        Optional allow-list; if provided, only matching-domain results
        are returned.
    blocked_domains:
        Optional block-list, evaluated before the allow-list.

    Returns
    -------
    dict
        ``{"status": "success", "results": [{"title", "url", "snippet"}]}``
        or ``{"status": "error", "error_message": str}``. Never raises.
    """
    blocked = blocked_domains if blocked_domains is not None else _DEFAULT_BLOCKED_DOMAINS
    allowed = allowed_domains if allowed_domains is not None else _DEFAULT_ALLOWED_DOMAINS

    try:
        client = _get_search_client()
        raw_results = client.search(query=query, max_results=max_results)

        filtered: list[dict[str, str]] = []
        for r in raw_results:
            url = r.get("url", "")
            if not _domain_allowed(url, allowed, blocked):
                continue
            filtered.append(
                {
                    "title": r.get("title", "")[:200],
                    "url": url,
                    "snippet": r.get("snippet", "")[:_MAX_SNIPPET_CHARS],
                }
            )

        return {"status": "success", "results": filtered, "count": len(filtered)}
    except NotImplementedError:
        logger.warning("Web search client not configured.")
        return {"status": "error", "error_message": "Web search is not configured yet."}
    except Exception as exc:  # noqa: BLE001 - tool boundary, must not raise
        logger.exception("search_tool failed for query=%r", query)
        return {"status": "error", "error_message": f"Web search failed: {exc}"}


search_tool = StructuredTool.from_function(
    func=search_web_for_product_info,
    name="search_tool",
    description=(
        "Search the public web for general product/manufacturer information "
        "(specs, compatibility, recalls, reviews) ONLY when the internal "
        "catalog (retriever_tool) has no answer. Never use for pricing, "
        "availability, order actions, or recommendations -- the internal "
        "catalog is always authoritative for those."
    ),
    args_schema=SearchToolInput,
)
