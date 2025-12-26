import asyncio
from typing import List, Dict, Any, Optional, Union
from uuid import UUID
from datetime import datetime

from loguru import logger
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, MatchAny

from server.core.config import settings
from server.core.llm import get_embeddings
from server.memory.schemas import MemoryItem, MemoryType

class VectorStoreManager:
    """
    向量存储管理器，封装 Qdrant 操作。
    单例模式。
    """
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorStoreManager, cls).__new__(cls)
            cls._instance.client = None
            cls._instance.collection_name = settings.MEMORY_COLLECTION
            cls._instance.embeddings = None
            cls._instance.vector_dim = settings.EMBEDDING_DIM
            cls._instance.initialized = False
        return cls._instance

    @classmethod
    async def get_instance(cls):
        """
        获取单例实例并确保初始化
        """
        if not cls._instance:
            cls._instance = cls()
        
        if not cls._instance.initialized:
            async with cls._lock:
                if not cls._instance.initialized:
                    await cls._instance.initialize()
        
        return cls._instance

    async def initialize(self):
        """
        初始化 Qdrant 连接和集合
        """
        if self.initialized:
            return

        try:
            logger.info(f"Initializing VectorStoreManager with Qdrant URL: {settings.QDRANT_URL}")
            self.client = AsyncQdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
            self.embeddings = get_embeddings()

            # Determine dimension dynamically
            try:
                # Generate a dummy embedding to get the actual dimension
                dummy_emb = await self.embeddings.aembed_query("test")
                if dummy_emb:
                    self.vector_dim = len(dummy_emb)
                    logger.info(f"Detected embedding dimension: {self.vector_dim}")
            except Exception as e:
                logger.warning(f"Could not determine embedding dimension dynamically, using configured default ({self.vector_dim}): {e}")

            # 检查并创建集合
            await self._ensure_collection()
            
            self.initialized = True
            logger.info(f"✅ VectorStoreManager initialized. Collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize VectorStoreManager: {e}")
            raise e

    async def _ensure_collection(self):
        """
        确保集合存在，如果不存在则创建
        """
        try:
            collection_info = await self.client.get_collection(self.collection_name)
            # 检查维度
            current_dim = collection_info.config.params.vectors.size
            if current_dim != self.vector_dim:
                logger.warning(f"⚠️ Collection '{self.collection_name}' dimension mismatch: Current={current_dim}, Configured={self.vector_dim}")
                logger.warning("Recreating collection...")
                await self.client.delete_collection(self.collection_name)
                await self._create_collection()
        except Exception:
            # 集合不存在
            await self._create_collection()

    async def _create_collection(self):
        """
        创建集合
        """
        logger.info(f"Creating Qdrant collection: {self.collection_name} with dim {self.vector_dim}")
        metric_map = {
            "cosine": Distance.COSINE,
            "euclidean": Distance.EUCLID,
            "dot": Distance.DOT
        }
        distance_metric = metric_map.get(settings.SIM_METRIC.lower(), Distance.COSINE)
        
        await self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.vector_dim, distance=distance_metric)
        )
        
        # 创建索引以加速过滤
        await self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="type",
            field_schema="keyword"
        )

    async def add_documents(self, items: List[MemoryItem]):
        """
        批量写入向量库
        """
        if not items:
            return

        points = []
        texts_to_embed = []
        items_to_embed_indices = []

        # 1. 准备数据，检查哪些需要生成向量
        for idx, item in enumerate(items):
            if not item.vector:
                texts_to_embed.append(item.content)
                items_to_embed_indices.append(idx)
        
        # 2. 批量生成向量
        if texts_to_embed:
            logger.debug(f"Generating embeddings for {len(texts_to_embed)} items...")
            vectors = await self.embeddings.aembed_documents(texts_to_embed)
            for i, vector in zip(items_to_embed_indices, vectors):
                items[i].vector = vector

        # 3. 构建 PointStruct
        for item in items:
            if not item.vector:
                logger.warning(f"Skipping item {item.id} because vector generation failed.")
                continue

            # 构建 Payload
            payload = item.metadata.copy()
            # 如果 use_enum_values=True, item.type 是 str
            memory_type = item.type.value if hasattr(item.type, "value") else item.type
            
            payload.update({
                "content": item.content,
                "type": memory_type,
                "timestamp": item.timestamp.isoformat(),
                "importance_score": item.importance_score
            })

            points.append(PointStruct(
                id=str(item.id),
                vector=item.vector,
                payload=payload
            ))

        # 4. 写入 Qdrant
        if points:
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Saved {len(points)} memory items to {self.collection_name}")

    async def search(self, query_vector: List[float], limit: int = 5, filter_dict: Dict[str, Any] = None) -> List[MemoryItem]:
        """
        向量搜索
        """
        query_filter = None
        if filter_dict:
            must_conditions = []
            for key, value in filter_dict.items():
                if isinstance(value, list):
                    must_conditions.append(FieldCondition(key=key, match=MatchAny(any=value)))
                else:
                    must_conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            
            if must_conditions:
                query_filter = Filter(must=must_conditions)

        results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter,
            with_payload=True
        )

        memory_items = []
        for hit in results:
            payload = hit.payload
            # 还原 MemoryItem
            # 注意：timestamp 存储为 isoformat string
            try:
                # 提取 metadata (排除基础字段)
                base_fields = {"content", "type", "timestamp", "importance_score"}
                metadata = {k: v for k, v in payload.items() if k not in base_fields}
                
                item = MemoryItem(
                    id=UUID(hit.id),
                    content=payload.get("content", ""),
                    vector=hit.vector if hit.vector else None,
                    type=MemoryType(payload.get("type")),
                    timestamp=datetime.fromisoformat(payload.get("timestamp")),
                    importance_score=payload.get("importance_score", 0.5),
                    similarity=hit.score if hasattr(hit, "score") else None,
                    metadata=metadata
                )
                memory_items.append(item)
            except Exception as e:
                logger.error(f"Error parsing memory item {hit.id}: {e}")
                continue

        return memory_items

    async def update_by_id(self, item_id: UUID, update_data: Dict[str, Any]):
        """
        更新记忆 (payload only)
        注意：如果需要更新向量，建议使用 delete + add
        """
        # 转换 timestamp 为 isoformat 如果存在
        if "timestamp" in update_data and isinstance(update_data["timestamp"], datetime):
            update_data["timestamp"] = update_data["timestamp"].isoformat()
            
        await self.client.set_payload(
            collection_name=self.collection_name,
            payload=update_data,
            points=[str(item_id)]
        )
        logger.info(f"Updated memory item {item_id}")

    async def delete_by_id(self, item_id: UUID):
        """
        删除记忆
        """
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(points=[str(item_id)])
        )
        logger.info(f"Deleted memory item {item_id}")

    async def scroll(self, limit: int = 100, filter_dict: Dict[str, Any] = None) -> List[MemoryItem]:
        """
        滚动获取记忆（非向量搜索）
        """
        query_filter = None
        if filter_dict:
            must_conditions = []
            for key, value in filter_dict.items():
                if isinstance(value, list):
                    must_conditions.append(FieldCondition(key=key, match=MatchAny(any=value)))
                else:
                    must_conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            
            if must_conditions:
                query_filter = Filter(must=must_conditions)
        
        # Scroll API
        response, _ = await self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        
        memory_items = []
        for point in response:
            payload = point.payload
            try:
                base_fields = {"content", "type", "timestamp", "importance_score"}
                metadata = {k: v for k, v in payload.items() if k not in base_fields}
                
                item = MemoryItem(
                    id=UUID(point.id),
                    content=payload.get("content", ""),
                    vector=None,
                    type=MemoryType(payload.get("type")),
                    timestamp=datetime.fromisoformat(payload.get("timestamp")),
                    importance_score=payload.get("importance_score", 0.5),
                    metadata=metadata
                )
                memory_items.append(item)
            except Exception as e:
                logger.error(f"Error parsing memory item {point.id}: {e}")
                continue
                
        return memory_items
