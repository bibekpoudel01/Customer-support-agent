import re
from typing import Optional

import logfire
from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.actions import action
from langchain_google_genai import ChatGoogleGenerativeAI
from src.guardrails.rails import COLANG_MAP
from langchain_groq import ChatGroq
YAML_MAP = """
models:
  - type: main
    engine: openai
    model: gpt-4o

instructions:
  - type: general
    content: |
      You are a Customer Support Assistant for an e-commerce platform. You help customers with
      product information (prices, stock availability, specifications, categories),
      order status, tracking, cancellations, billing, invoices, payment
      methods, returns and refunds, warranty claims, delivery issues, and
      account/login questions. Only answer using grounded product, order,
      and account data — never guess or state a fact you cannot verify
      from retrieved data. If information isn't available, say so rather
      than answering. Stay strictly within this scope. Do not access,
      guess, or discuss any other customer's account or personal data.
      Do not help bypass identity or payment verification.

rails:
  input:
    flows:
      - PII detection
      - classify urgency
  
"""

@action(is_system_action=True)
async def detect_pii_in_input(context: Optional[dict] = None):
    """Returns list of PII type names found, or empty list (falsy) if clean."""
    user_message = context.get("user_message", "") if context else ""

    patterns = {
        "email":       r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "phone":       r"\b(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b",
        "ssn":         r"\b\d{3}-\d{2}-\d{4}\b",
        "api_key":     r"(api[_\s-]?key|token|secret)[:\s]+[A-Za-z0-9_\-]{10,}",
        "credit_card": r"\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b",
    }
    found = [ptype for ptype, pat in patterns.items()
             if re.search(pat, user_message, re.IGNORECASE)]
    return found


@action(is_system_action=True)
async def classify_urgency(context: Optional[dict] = None):
    """Returns True if the message signals a production emergency."""
    msg = (context.get("user_message", "") if context else "").lower()
    urgent_keywords = [
        "outage", "down", "crash", "critical",
        "emergency", "not working", "urgent", "p0", "p1",
    ]
    return any(kw in msg for kw in urgent_keywords)


RAIL_INDICATORS = [
    "I'm a Customer Support Assistant focused on providing information about products , orders, billing, and account help",
    "I maintain consistent guidelines regardless of how I am prompted",
    "I can't help with accessing accounts or data that aren't yours",
    "Hello! I'm your Customer Support Assistant",
    "Goodbye! Feel free to come back anytime you have questions about your orders",
    "For your security, please don't share sensitive personal info",
    "This sounds urgent",
]


_RAILS_ENGINE: Optional[LLMRails] = None

#def _build_llm() -> ChatGoogleGenerativeAI:
#    return ChatGoogleGenerativeAI(model="gemini-2.5-flash")
def _build_llm() -> ChatGroq:
    return ChatGroq(model="openai/gpt-oss-120b", temperature=0.0)

def get_rails_config() -> RailsConfig:
    return RailsConfig.from_content(
        colang_content=COLANG_MAP,
        yaml_content=YAML_MAP,
    )


def initialize_rails() -> None:
    """Builds the single module-level rails engine used by guard()."""
    global _RAILS_ENGINE
    config = get_rails_config()
    engine = LLMRails(config, llm=_build_llm())
    engine.register_action(detect_pii_in_input, "detect_pii_in_input")
    engine.register_action(classify_urgency, "classify_urgency")
    _RAILS_ENGINE = engine
    logfire.info("🛡️ Guardrails initialized.")


async def guard(message: str):
    if _RAILS_ENGINE is None:
        raise RuntimeError("Guardrails not initialized. Call initialize_rails() first.")

    result = await _RAILS_ENGINE.generate_async(
        messages=[{"role": "user", "content": message}]
    )
    content = result.get("content", "") if isinstance(result, dict) else str(result)
    fired = any(indicator.lower() in content.lower() for indicator in RAIL_INDICATORS)
    return fired, content