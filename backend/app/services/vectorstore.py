"""Qdrant: Qdrant Cloud when QDRANT_CLUSTER_ENDPOINT is set, otherwise embedded local storage in backend/.qdrant."""

import uuid

from app.config import settings

_client = None


def client():
    global _client
    if _client is None:
        from qdrant_client import QdrantClient

        _client = (QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
                   if settings.QDRANT_URL else QdrantClient(path=settings.QDRANT_LOCAL_PATH))
    return _client


def recreate_collection(wipe: bool = False) -> None:
    from qdrant_client.http import models

    c, name = client(), settings.QDRANT_COLLECTION
    if wipe and c.collection_exists(name):
        c.delete_collection(name)
    if not c.collection_exists(name):
        c.create_collection(name, vectors_config=models.VectorParams(size=settings.EMBEDDING_DIM, distance=models.Distance.COSINE))


def upsert_chunks(chunks: list[dict], vectors: list[list[float]]) -> int:
    from qdrant_client.http import models

    points = [
        models.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, ch["id"])), vector=v, payload=ch)
        for ch, v in zip(chunks, vectors)
    ]
    client().upsert(settings.QDRANT_COLLECTION, points=points)
    return len(points)


def search(vector: list[float], limit: int = 15) -> list[dict]:
    c = client()
    if not c.collection_exists(settings.QDRANT_COLLECTION):
        return []
    res = c.query_points(settings.QDRANT_COLLECTION, query=vector, limit=limit, with_payload=True)
    return [{**p.payload, "score": p.score} for p in res.points]
