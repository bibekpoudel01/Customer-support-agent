import os
from dotenv import load_dotenv

load_dotenv(override=True)


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_FALLBACK_API_KEY = os.getenv("GROQ_FALLBACK_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

    # --- LLM Gateway (Portkey) ---
PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY")
PORTKEY_CONFIG_ID = os.getenv("PORTKEY_CONFIG_ID")
PORTKEY_GATEWAY_URL = os.getenv("PORTKEY_GATEWAY_URL", "https://api.portkey.ai/v1")
GROQ_SLUG = "rag"    
GROQ_SLUG_2 = "brag"  

    
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
USE_SEMANTIC_CACHE = os.getenv("USE_SEMANTIC_CACHE", "false").lower() == "true"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
     # --- Observability ---
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "true")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "entreprise_rag")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
JUDGE_GROQ = os.getenv("JUDGE_GROQ")
DATA_DIR = os.getenv("RAG_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "DATA", "True_Data"))
     
        