import os
from dotenv import load_dotenv

load_dotenv(override=True)


class Settings:
    # --- LLM (Groq) ---
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_FALLBACK_API_KEY = os.getenv("GROQ_FALLBACK_API_KEY")
    GROQ_MODEL = "llama-3.3-70b-versatile"

    # --- LLM Gateway (Portkey) ---
    PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY")
    PORTKEY_CONFIG_ID = os.getenv("PORTKEY_CONFIG_ID")
    PORTKEY_GATEWAY_URL = os.getenv("PORTKEY_GATEWAY_URL", "https://api.portkey.ai/v1")
    GROQ_SLUG = "rag"     # primary virtual key: @rag/llama-3.3-70b-versatile
    GROQ_SLUG_2 = "brag"  # fallback virtual key: @brag/llama-3.1-8b-instant

    # --- Guardrails (NVIDIA) ---
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    USE_SEMANTIC_CACHE = os.getenv("USE_SEMANTIC_CACHE", "false").lower() == "true"

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
     
        