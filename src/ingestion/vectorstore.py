import os
from typing import List
from flashrank import Ranker
import logfire
from dotenv import load_dotenv
from langchain_community.document_compressors import FlashrankRerank
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import FastEmbedSparse, QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, SparseVectorParams, VectorParams
from langchain_classic.retrievers import ContextualCompressionRetriever
load_dotenv()
FlashrankRerank.model_rebuild()
GLOBAL_COLLECTION_NAME = "customer_support_agent_collection1"

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL", "http://localhost:6333"),
    api_key=os.getenv("QDRANT_API_KEY", ""),
    timeout=30,
)


def ensure_collection_exist(collection_name: str) -> None:
    """
    Ensure that the Qdrant collection exists. If it doesn't, create it.
    """
    if not qdrant_client.collection_exists(collection_name):
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config={"dense": VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE)},
            sparse_vectors_config={
                "sparse": SparseVectorParams(index=models.SparseIndexParams(on_disk=False))
            },
        )

        qdrant_client.create_payload_index(
            collection_name=collection_name,
            field_name="metadata.session_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )


def get_vectorstore(session_id: str) ->ContextualCompressionRetriever :
    ensure_collection_exist(GLOBAL_COLLECTION_NAME)

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")

    session_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="metadata.session_id",
                match=models.MatchValue(value=session_id),
            ),
        ]
    )


    qdrant_vs = QdrantVectorStore(
        client=qdrant_client,
        collection_name=GLOBAL_COLLECTION_NAME,
        embedding=embeddings,
        sparse_embedding=sparse_embeddings,
        retrieval_mode=RetrievalMode.HYBRID,
        vector_name="dense",
        sparse_vector_name="sparse",
    )

    reranker = FlashrankRerank(top_n=2)
    base_retriever = qdrant_vs.as_retriever(
        search_kwargs={
            "k": 8,
            "filter": session_filter,
        }
    )

    return ContextualCompressionRetriever(
        base_compressor=reranker,
        base_retriever=base_retriever,
    )


def add_page(docs: List[Document], session_id: str) -> None:
    """
    Add a list of documents to the Qdrant vector store with the specified session ID.
    """
    for doc in docs:
        doc.metadata["session_id"] = session_id

    retriever = get_vectorstore(session_id)
    vectorstore = retriever.base_retriever.vectorstore
    vectorstore.add_documents(docs)



def build_vectorstore(documents: List[Document], session_id: str) -> ContextualCompressionRetriever:
    for doc in documents:
        doc.metadata["session_id"] = session_id

    retriever_pipeline = get_vectorstore(session_id)
    vectorstore = retriever_pipeline.base_retriever.vectorstore

    # Upload in batches instead of all at once
    batch_size = 500
    total = len(documents)
    for i in range(0, total, batch_size):
        batch = documents[i : i + batch_size]
        vectorstore.add_documents(batch)
        logfire.info(
            f"📤 Uploaded batch {i // batch_size + 1}/"
            f"{(total + batch_size - 1) // batch_size} ({len(batch)} chunks)"
        )

    return retriever_pipeline


def list_papers(session_id: str) -> List[str]:
    """Scrolls through the global collection payload to retrieve unique paper titles for a specific session."""
    if not qdrant_client.collection_exists(GLOBAL_COLLECTION_NAME):
        return []
   

    seen = set()
    titles = []
    offset = None

    session_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="metadata.session_id",
                match=models.MatchValue(value=session_id),
            )
        ]
    )

    while True:
        points, offset = qdrant_client.scroll(
            collection_name=GLOBAL_COLLECTION_NAME,
            scroll_filter=session_filter,  # only fetch points belonging to this session
            with_payload=True,
            limit=100,
            offset=offset,
        )

        for point in points:
            title = (point.payload or {}).get("metadata", {}).get("title")
            if title and title not in seen:
                seen.add(title)
                titles.append(title)

        if offset is None:
            break

    return titles


def search(query: str, session_id: str = None) -> List[Document]:
    if session_id is None:
        raise ValueError("session_id is required")

    retriever = get_vectorstore(session_id)
    return retriever.invoke(query)

