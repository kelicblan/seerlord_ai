from datetime import datetime
import json
import uuid
from typing import List, Dict, Any, Optional
from loguru import logger
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from server.core.config import settings
from server.core.llm import get_embeddings

class MemoryManager:
    """
    Long-term memory manager using Qdrant.
    Singleton pattern.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MemoryManager, cls).__new__(cls)
            cls._instance.client = None
            cls._instance.embeddings = None
            cls._instance.enabled = False
        return cls._instance

    async def initialize(self):
        """
        Initialize the Qdrant connection and ensure collection exists.
        """
        if not settings.QDRANT_URL:
            logger.warning("⚠️ No QDRANT_URL found. MemoryManager is DISABLED.")
            return

        try:
            self.embeddings = get_embeddings()
            
            # Initialize Qdrant Client
            self.client = AsyncQdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
            
            # Check if collection exists
            collection_name = settings.QDRANT_COLLECTION
            try:
                collection_info = await self.client.get_collection(collection_name)
                exists = True
                # Check dimension compatibility
                current_dim = collection_info.config.params.vectors.size
                if current_dim != settings.EMBEDDING_DIM:
                    logger.warning(f"⚠️ Collection '{collection_name}' dimension mismatch: Current={current_dim}, Configured={settings.EMBEDDING_DIM}")
                    logger.warning("Recreating collection to match new embedding model dimensions...")
                    await self.client.delete_collection(collection_name)
                    exists = False
            except Exception:
                # Collection does not exist or error fetching info
                exists = False
            
            if not exists:
                logger.info(f"Creating Qdrant collection: {collection_name}")
                
                # Map metric string to Qdrant Distance enum
                metric_map = {
                    "cosine": Distance.COSINE,
                    "euclidean": Distance.EUCLID,
                    "dot": Distance.DOT
                }
                distance_metric = metric_map.get(settings.SIM_METRIC.lower(), Distance.COSINE)
                
                await self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=settings.EMBEDDING_DIM,
                        distance=distance_metric
                    )
                )
            
            self.enabled = True
            logger.info(f"✅ MemoryManager initialized (Qdrant: {settings.QDRANT_URL}, Collection: {collection_name})")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize MemoryManager: {e}")
            self.enabled = False

    async def save_experience(self, content: str, agent_name: str, session_id: str, tenant_id: str, user_id: str = None, metadata: Dict[str, Any] = None):
        """
        Save a text fragment to memory with agent, session, tenant and optional user context.
        """
        if not self.enabled: return
        
        try:
            # 1. Generate Embedding
            vector = await self.embeddings.aembed_query(content)
            
            # 2. Create Point
            point_id = str(uuid.uuid4())
            payload = metadata or {}
            payload["content"] = content
            payload["agent_name"] = agent_name
            payload["session_id"] = session_id
            payload["tenant_id"] = tenant_id  # Multi-Tenancy Key
            if user_id:
                payload["user_id"] = user_id
            payload["created_at"] = datetime.now().isoformat()
            
            # 3. Upsert
            await self.client.upsert(
                collection_name=settings.QDRANT_COLLECTION,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            logger.debug(f"Saved memory for agent='{agent_name}' (Tenant: {tenant_id}, User: {user_id}): {content[:30]}...")
            
        except Exception as e:
            logger.error(f"Failed to save experience: {e}")

    async def retrieve_relevant(self, query: str, tenant_id: str, user_id: str = None, agent_name: str = None, k: int = 5, threshold: float = 0.7) -> List[Dict]:
        """
        Retrieve relevant memories. 
        CRITICAL: Always filters by tenant_id to prevent data leakage.
        Optionally filters by user_id if provided.
        """
        if not self.enabled: return []
        
        try:
            vector = await self.embeddings.aembed_query(query)
            
            # Base Filter: Must match tenant_id
            must_conditions = [
                models.FieldCondition(
                    key="tenant_id",
                    match=models.MatchValue(value=tenant_id)
                )
            ]
            
            # Optional Filter: Match user_id
            if user_id:
                must_conditions.append(
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id)
                    )
                )
            
            # Optional Filter: Match agent_name
            if agent_name:
                must_conditions.append(
                    models.FieldCondition(
                        key="agent_name",
                        match=models.MatchValue(value=agent_name)
                    )
                )

            query_filter = models.Filter(must=must_conditions)

            search_result = await self.client.query_points(
                collection_name=settings.QDRANT_COLLECTION,
                query=vector,
                query_filter=query_filter,
                limit=k,
                score_threshold=threshold
            )
            
            results = []
            for hit in search_result.points:
                payload = hit.payload or {}
                results.append({
                    "content": payload.get("content", ""),
                    "metadata": payload,
                    "similarity": hit.score,
                    "created_at": payload.get("created_at"),
                    "agent_name": payload.get("agent_name"),
                    "session_id": payload.get("session_id"),
                    "tenant_id": payload.get("tenant_id"),
                    "user_id": payload.get("user_id")
                })
            return results
            
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {e}")
            return []
            
    async def close(self):
        if self.client:
            await self.client.close()

# Global instance
memory_manager = MemoryManager()
