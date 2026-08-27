import logfire
from portkey_ai import Portkey, createHeaders, PORTKEY_GATEWAY_URL
from langchain_openai import ChatOpenAI
from src.config.config import *

GATEWAY_CONFIG_CACHED = {
    "strategy": {"mode": "fallback"},
    "cache": {"mode": "semantic", "age": 500},
    "retry": {
        "attempts": 2,
        "on_status_codes": [429, 503]
    },
    "targets": [
        {"override_params": {"model": f"@{GROQ_SLUG}/llama-3.3-70b-versatile"}},
        {"override_params": {"model": f"@{GROQ_SLUG_2}/llama-3.1-8b-instant"}},
    ]
}


portkey_client = Portkey(
    api_key=PORTKEY_API_KEY,
    config=GATEWAY_CONFIG_CACHED,
    base_url=PORTKEY_GATEWAY_URL,
)

def get_langchain_llm(feature: str = "rag") -> ChatOpenAI:
    """Returns a LangChain ChatOpenAI instance configured to use Portkey with the specified feature."""
    config = GATEWAY_CONFIG_CACHED
    return ChatOpenAI(
        api_key=PORTKEY_API_KEY,
        base_url=PORTKEY_GATEWAY_URL,
        model=f"@{GROQ_SLUG}/llama-3.3-70b-versatile",
        temperature=0,
        default_headers=createHeaders(
            api_key=PORTKEY_API_KEY,
            config=config,
            metadata={"feature": feature, "_user": "rag-system", "environment": "production"}
        )
    )



#Returns the cached response when the exact same request is sent again.
def extract_cache_status(response) -> str:
    """
    Pull x-portkey-cache-status from the Portkey native client response headers.
    Tries multiple attribute paths defensively — returns 'MISS' if not found.
    """
    for attr in ("_raw_response", "_response", "_http_response"):
        raw = getattr(response, attr, None)
        if raw is not None:
            status = getattr(raw, "headers", {}).get("x-portkey-cache-status", "")
            if status:
                return status.upper()
    return "MISS"


