from qdrant_client import AsyncQdrantClient, models
from server.core.config import settings
from loguru import logger
import uuid
from typing import Callable, Awaitable, Any

class QdrantService:
    def __init__(self):
        self.client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self.base_collection_name = settings.QDRANT_COLLECTION
        self.vector_size = settings.EMBEDDING_DIM

    def get_collection_name(self, kb_id: str | None) -> str:
        if not kb_id:
            return self.base_collection_name
        return f"{self.base_collection_name}__kb__{kb_id}"

    async def ensure_collection(self, kb_id: str | None = None, vector_size: int | None = None):
        """
        Check if collection exists, create if not.
        Must be called async.
        """
        collection_name = self.get_collection_name(kb_id)
        dim = vector_size or self.vector_size
        try:
            exists = await self.client.collection_exists(collection_name)
            if not exists:
                logger.info(f"Creating Qdrant collection: {collection_name} with dim {dim}")
                await self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=dim,
                        distance=models.Distance.COSINE
                    )
                )
            else:
                # Optional: Check if existing collection has same dimension
                # If mismatch, we might need to warn or recreate (not implemented here for safety)
                pass
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {e}")
            raise

    async def upsert_documents(
        self,
        kb_id: str,
        doc_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
        progress_cb: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ):
        """
        Upload vectors to Qdrant.
        """
        collection_name = self.get_collection_name(kb_id)
        points = []
        for i, (text, vector) in enumerate(zip(chunks, embeddings)):
            points.append(models.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "kb_id": kb_id,
                    "doc_id": doc_id,
                    "text": text,
                    "chunk_index": i
                }
            ))
        
        if not points:
            return

        # Batch upsert
        batch_size = 100
        total_batches = (len(points) + batch_size - 1) // batch_size
        for i in range(0, len(points), batch_size):
            batch = points[i:i+batch_size]
            if progress_cb:
                await progress_cb(
                    {
                        "phase": "upsert_batch_start",
                        "batch_index": (i // batch_size) + 1,
                        "total_batches": total_batches,
                        "batch_size": len(batch),
                        "total_points": len(points),
                    }
                )
            await self.client.upsert(
                collection_name=collection_name,
                points=batch
            )
            if progress_cb:
                await progress_cb(
                    {
                        "phase": "upsert_batch_done",
                        "batch_index": (i // batch_size) + 1,
                        "total_batches": total_batches,
                        "batch_size": len(batch),
                        "total_points": len(points),
                    }
                )
        
        logger.info(f"Upserted {len(points)} chunks for doc {doc_id} in kb {kb_id}")

    async def search(self, query_vector: list[float], kb_id: str = None, limit: int = 50):
        """
        Search for similar vectors.
        """
        collection_name = self.get_collection_name(kb_id)
        
        results = await self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )
        return results

    async def delete_document(self, doc_id: str, kb_id: str | None = None):
        """
        Delete all points for a specific document.
        """
        collection_name = self.get_collection_name(kb_id)
        await self.client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="doc_id",
                            match=models.MatchValue(value=doc_id)
                        )
                    ]
                )
            )
        )

    async def list_document_chunks(self, doc_id: str, kb_id: str | None = None, limit: int = 200, offset: str | None = None):
        collection_name = self.get_collection_name(kb_id)
        must = [
            models.FieldCondition(
                key="doc_id",
                match=models.MatchValue(value=doc_id),
            )
        ]

        points, next_offset = await self.client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(must=must),
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        return points, next_offset

    async def delete_kb_collection(self, kb_id: str) -> None:
        collection_name = self.get_collection_name(kb_id)
        try:
            exists = await self.client.collection_exists(collection_name)
            if not exists:
                return
            await self.client.delete_collection(collection_name=collection_name)
        except Exception as e:
            logger.error(f"Failed to delete Qdrant collection {collection_name}: {e}")
            raise
