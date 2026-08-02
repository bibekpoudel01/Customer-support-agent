import os
import json
import hashlib
import numpy as np
import logfire

DISTANCE_THRESHOLD = float(os.getenv("CACHE_DISTANCE_THRESHOLD", "0.15"))
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
KEY_PREFIX = "sem_cache:"


_client = None
_encoder = None


def _get_client():
    """Connects to free local Redis by default"""
    global _client
    if _client is not None:
        return _client

    import redis

    _client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"), 
        port=int(os.getenv("REDIS_PORT", "6379")),
        socket_connect_timeout=2,
        socket_timeout=2,
        decode_responses=False,
    )
    return _client


def _embed_query_local(query: str) -> list[float]:
    """Generates embeddings locally on your machine for FREE"""
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer
    
        _encoder = SentenceTransformer("all-MiniLM-L6-v2")
    
    embedding = _encoder.encode(query)
    return embedding.tolist()


def _cosine_distance(a, b) -> float:
    a, b = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 1.0
    return float(1.0 - np.dot(a, b) / (norm_a * norm_b))


def check_cache(query: str) -> str | None:
    """Returns a cached answer if a semantically similar query exists"""
    if os.getenv("USE_SEMANTIC_CACHE", "false").lower() != "true":
        return None

    try:
        client = _get_client()
        query_vec = _embed_query_local(query)

        for key in client.scan_iter(f"{KEY_PREFIX}*"):
            raw = client.get(key)
            if raw is None:
                continue
            entry = json.loads(raw)
            dist = _cosine_distance(query_vec, entry["embedding"])
            if dist < DISTANCE_THRESHOLD:
                logfire.info(f"⚡ Cache HIT (distance={dist:.3f}) for: {query[:60]}")
                return entry["answer"]

    except Exception as e:
        logfire.warning(f"⚠️ Semantic cache check failed (non-fatal): {e}")

    return None


def set_cache(query: str, answer: str) -> None:
    """Stores query embedding + answer in local Redis with a TTL"""
    if os.getenv("USE_SEMANTIC_CACHE", "false").lower() != "true":
        return

    try:
        client = _get_client()
        embedding = _embed_query_local(query)

        entry = {
            "query": query,
            "answer": answer,
            "embedding": embedding,
        }

        key = f"{KEY_PREFIX}{hashlib.md5(query.encode()).hexdigest()}"
        client.set(key, json.dumps(entry), ex=CACHE_TTL)
        logfire.info(f"💾 Cached answer for: {query[:60]}")

    except Exception as e:
        logfire.warning(f"⚠️ Semantic cache set failed (non-fatal): {e}")