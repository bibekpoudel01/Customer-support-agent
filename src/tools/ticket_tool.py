"""
ticket_tool.py
===============
Tool used EXCLUSIVELY by the Escalation Agent to open human-support
tickets when a request falls outside automated resolution.

Guardrails
----------
- This is the only tool in the system permitted to create a ticket --
  no other agent should ever escalate directly; they should return
  ``status="needs_escalation"``-style signals and let the Planner route
  to the Escalation agent instead.
- Severity is constrained to an enum to keep triage queues consistent.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

Severity = Literal["low", "medium", "high", "urgent"]


def _get_ticketing_client() -> Any:
    """Lazily import the ticketing system client (e.g. Zendesk, Freshdesk, internal)."""
    raise NotImplementedError("Wire this up to your ticketing system client.")


class CreateTicketInput(BaseModel):
    subject: str = Field(..., description="Short ticket subject line.")
    description: str = Field(..., description="Full context for the human agent, including what was already tried.")
    severity: Severity = Field(default="medium", description="Triage severity.")
    customer_id: str | None = Field(default=None, description="Customer ID if known.")
    order_id: str | None = Field(default=None, description="Related order ID, if applicable.")


def create_support_ticket(
    subject: str,
    description: str,
    severity: Severity = "medium",
    customer_id: str | None = None,
    order_id: str | None = None,
) -> dict[str, Any]:
    """Create a human support ticket for issues automation cannot resolve.

    Returns
    -------
    dict
        ``{"status": "success", "ticket_id": ..., "eta": ...}`` or an
        error dict. Never raises.
    """
    try:
        client = _get_ticketing_client()
        ticket = client.create_ticket(
            subject=subject,
            description=description,
            severity=severity,
            customer_id=customer_id,
            order_id=order_id,
        )
        return {"status": "success", "ticket_id": ticket["id"], "eta": ticket.get("eta")}
    except NotImplementedError:
        logger.warning("Ticketing client not configured.")
        return {"status": "error", "error_message": "Ticketing system is not configured yet."}
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_support_ticket failed for subject=%r", subject)
        return {"status": "error", "error_message": f"Ticket creation failed: {exc}"}


ticket_tool = StructuredTool.from_function(
    func=create_support_ticket,
    name="ticket_tool",
    description=(
        "Create a human support ticket for issues that cannot be resolved "
        "automatically (complaints, fraud, policy exceptions, repeated "
        "failures). Use ONLY when automated resolution is not possible."
    ),
    args_schema=CreateTicketInput,
)
