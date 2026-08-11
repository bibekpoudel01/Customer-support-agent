import os
import sys
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

import logfire
from dotenv import load_dotenv
from fastapi import FastAPI, Response
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv(override=True)
logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))

from src.config.config import Config
from src.guardrails.actions import initialize_rails, guard
from src.ingestion.vectorstore import GLOBAL_COLLECTION_NAME

config_instance = Config()
GLOBAL_DEFAULT_SESSION = "default_user"
FALLBACK_ANSWER = "Sorry, something went wrong. Please try again."

_RAG_AGENT = None

USE_SEMANTIC_CACHE = os.getenv("USE_SEMANTIC_CACHE", "false").lower() == "true"
if USE_SEMANTIC_CACHE:
    try:
        from src.services.redis_semantic import check_cache, set_cache
    except ImportError as e:
        logfire.error(f"Failed to import Redis semantic cache modules: {e}")
        USE_SEMANTIC_CACHE = False


def _collection_already_populated() -> bool:
    """Check whether the Qdrant collection already has data, so we can
    skip re-ingesting documents on every startup."""
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
        collection_name = getattr(config_instance, "collection_name", GLOBAL_COLLECTION_NAME)

        if client.collection_exists(collection_name=collection_name):
            info = client.get_collection(collection_name=collection_name)
            if info and info.points_count > 0:
                logfire.info(f"Qdrant collection '{collection_name}' already populated. Skipping ingestion.")
                return True
        return False
    except Exception as db_check_err:
        logfire.warning(f"Qdrant verification skipped ({db_check_err}). Falling back to ingestion check.")
        return False


def _run_ingestion() -> None:
    """Load, chunk, and embed source documents into the vector store."""
    target_data_directory = config_instance.data_dir
    if not (os.path.exists(target_data_directory) and os.listdir(target_data_directory)):
        logfire.warning(f"Ingestion skipped: target directory '{target_data_directory}' is empty.")
        return

    try:
        logfire.info("Processing source documents ingestion flow...")
        from src.ingestion.data_loader import document_loader as load_documents
        from src.ingestion.chunking.splitter import create_semantic_chunks
        from src.ingestion.vectorstore import build_vectorstore

        raw_docs = load_documents([target_data_directory])
        if not raw_docs:
            return

        semantic_chunks = create_semantic_chunks(raw_docs)
        if semantic_chunks:
            build_vectorstore(documents=semantic_chunks, session_id=GLOBAL_DEFAULT_SESSION)
            logfire.info("Vector store setup finalized.")
    except Exception as ingestion_error:
        logfire.error(f"Ingestion pipeline failed: {ingestion_error}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _RAG_AGENT

    try:
        initialize_rails()
    except Exception as e:
        logfire.error(f"Guardrails init failed: {e}")

    try:
        from src.sql.database import init_db
        init_db()
    except Exception as e:
        logfire.error(f"DB init failed: {e}")

    if not _collection_already_populated():
        _run_ingestion()

    from src.agent.graph import app as compiled_graph
    _RAG_AGENT = compiled_graph
    yield


app = FastAPI(title="Enterprise Agentic RAG API", lifespan=lifespan)


class QueryRequest(BaseModel):
    q: str
    thread_id: Optional[str] = GLOBAL_DEFAULT_SESSION


@app.get("/")
async def home():
    return {"message": "Enterprise LangGraph RAG API is live."}


@app.get("/graph")
async def get_graph_image():
    if _RAG_AGENT is None:
        return {"error": "RAG Agent graph context has not been initialized."}
    try:
        png_bytes = _RAG_AGENT.get_graph().draw_mermaid_png()
        return Response(content=png_bytes, media_type="image/png")
    except Exception as e:
        return {"error": f"Failed to render runtime Agent graph schema: {e}"}


@app.post("/query")
async def query(request: QueryRequest):
    q = request.q
    thread_id = request.thread_id or GLOBAL_DEFAULT_SESSION

    if USE_SEMANTIC_CACHE:
        cached = await asyncio.to_thread(check_cache, q)
        if cached:
            return {"question": q, "answer": cached, "status": "cache_hit"}

    rail_fired, rail_response = await guard(q)
    if rail_fired:
        return {"question": q, "answer": rail_response, "status": "blocked"}

    if _RAG_AGENT is None:
        return {"question": q, "answer": "RAG not initialized", "status": "error"}

    initial_state = {
        "messages": [{"role": "user", "content": q}],
        "current_query": q,
        "documents": [],
        "plan": ["Start"],
        "status": "Initializing Graph...",
        "session_id": thread_id,
    }
    config = {"configurable": {"thread_id": thread_id}}

    try:
        
        final_output = await _RAG_AGENT.ainvoke(initial_state, config=config)
        answer = final_output.get("final_answer", FALLBACK_ANSWER)

        if USE_SEMANTIC_CACHE and answer:
            try:
                await asyncio.to_thread(set_cache, q, answer)
            except Exception as cache_err:
                logfire.warning(f"Cache write failed: {cache_err}")

        return {
            "question": q,
            "answer": answer,
            "status": final_output.get("status", "success"),
            "sources": final_output.get("documents", []),
        }
    except Exception as e:
        logfire.error(f"Query failed for thread '{thread_id}': {e}")
        return {"question": q, "answer": FALLBACK_ANSWER, "status": "error"}