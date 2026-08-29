import os
import sys
import uuid
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
import logfire
from dotenv import load_dotenv
from fastapi import FastAPI, Response
from pydantic import BaseModel
load_dotenv(override=True)
logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from src.config.config import *
from src.config.config import DATA_DIR
from src.guardrails.actions import initialize_rails, guard
from src.ingestion.vectorstore import GLOBAL_COLLECTION_NAME
from src.ingestion.data_loader.document_loader import load_documents
from src.ingestion.chunking.splitter import create_semantic_chunks
from src.ingestion.vectorstore import build_vectorstore,add_page,list_papers



from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from src.services.database_services import get_async_db_pool
from src.agent.graph import create_graph
from src.sql.database import init_db
from langgraph.checkpoint.memory import MemorySaver
HERE = Path(__file__).parent

PRODUCT_SOURCE = HERE / "sql" / "product.json"
from src.sql.ingest_product import load_products

GLOBAL_DEFAULT_SESSION = "default_user"
FALLBACK_ANSWER = "Sorry, something went wrong. Please try again."

_RAG_AGENT = None

USE_SEMANTIC_CACHE = os.getenv("USE_SEMANTIC_CACHE", "false").lower() == "true"
from src.services.redis_semantic import check_cache, set_cache





def _collection_already_populated() -> bool:
    """Check whether the Qdrant collection already has data, so we can
    skip re-ingesting documents on every startup."""
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
        collection_name = GLOBAL_COLLECTION_NAME

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
    target_data_directory = Path(DATA_DIR)

    if not target_data_directory.exists() or not target_data_directory.is_dir():
        logfire.warning(
            f"Ingestion skipped: target directory '{target_data_directory}' does not exist."
        )
        return
    source_files = [str(file_path)
                     for file_path in target_data_directory.iterdir() 
                     if file_path.is_file()]

    if not source_files:
        logfire.warning(
            f"Ingestion skipped: target directory '{target_data_directory}' is empty."
        )
        return

    try:
        logfire.info(f"Processing source documents ingestion flow... Found {len(source_files)} files.")
        raw_docs = load_documents(source_files)
        if not raw_docs:
            logfire.warning("No documents were successfully loaded.")
            return

        logfire.info(f"Successfully loaded {len(raw_docs)} documents.")
        semantic_chunks = create_semantic_chunks(raw_docs)
        if semantic_chunks:
            logfire.info(f"Created {len(semantic_chunks)} semantic chunks.")
            build_vectorstore(
                documents=semantic_chunks,
                session_id=GLOBAL_DEFAULT_SESSION
            )
            logfire.info("Vector store setup finalized.")
        else:
            logfire.warning("No semantic chunks were created.")

    except Exception as ingestion_error:
        logfire.error(f"Ingestion pipeline failed: {ingestion_error}")
        raise


def _initialize_sql_database() -> None:
    """
    Initialize SQLite database and load product seed data.
    SQLite products.db is completely separate from
    PostgreSQL used by LangGraph checkpointing.
    """
    try:
        init_db()
        logfire.info("✅ SQL database tables initialized.")
        if not PRODUCT_SOURCE.exists():
            logfire.warning(f"Product JSON not found: {PRODUCT_SOURCE}")
            return

        load_products(str(PRODUCT_SOURCE))
        logfire.info("✅ Product data loaded into products.db.")

    except Exception as e:
        logfire.exception(f"❌ SQL database initialization failed: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _RAG_AGENT
    async_pool = None
    try:
        initialize_rails()
    except Exception as e:
        logfire.error(f"Guardrails init failed: {e}")
    try:
        _initialize_sql_database()
    except Exception as e:
        logfire.error(f"SQL DB init failed: {e}")

    if not _collection_already_populated():
        _run_ingestion()

    try:
        async_pool = await get_async_db_pool()

        if async_pool is not None:
            checkpointer = AsyncPostgresSaver(async_pool)
            await checkpointer.setup()
            _RAG_AGENT = create_graph(checkpointer)
            logfire.info("✅ LangGraph initialized with AsyncPostgresSaver")
        else:
            _RAG_AGENT = create_graph(MemorySaver())
            logfire.warning("⚠️ Async Postgres unavailable — using MemorySaver")
    except Exception as e:
        logfire.exception(f"❌ LangGraph initialization failed: {e}")
        raise
    yield

   
    if async_pool is not None:
        await async_pool.close()

        logfire.info( "✅ Async Postgres connection pool closed")




app = FastAPI(title="Customer Support Agent API", lifespan=lifespan)


class QueryRequest(BaseModel):
    q: str
    thread_id: Optional[str] = None


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
    thread_id = request.thread_id or f"anon-{uuid.uuid4()}"

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
        logfire.exception(
            f"Query failed for thread '{thread_id}'"
        )

        return {
            "question": q,
            "answer": FALLBACK_ANSWER,
            "status": "error",
            "error": repr(e),
        }