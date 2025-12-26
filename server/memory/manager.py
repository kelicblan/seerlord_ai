import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4

from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage

from server.core.llm import get_llm, get_embeddings
from server.memory.schemas import MemoryItem, MemoryType, UserProfile
from server.memory.storage import VectorStoreManager

class MemoryManager:
    """
    记忆管理器核心逻辑
    负责协调短期记忆、长期记忆、用户画像的存储与检索。
    """
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MemoryManager, cls).__new__(cls)
            cls._instance.storage = None
            cls._instance.llm = None
            cls._instance.embeddings = None
            cls._instance.initialized = False
        return cls._instance

    @classmethod
    async def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()
        
        if not cls._instance.initialized:
            async with cls._lock:
                if not cls._instance.initialized:
                    await cls._instance.initialize()
        
        return cls._instance

    async def initialize(self):
        if self.initialized:
            return
        
        self.storage = await VectorStoreManager.get_instance()
        self.llm = get_llm(temperature=0.0) # Low temp for analysis
        self.embeddings = get_embeddings()
        self.initialized = True
        logger.info("✅ MemoryManager initialized")

    async def add_interaction(self, user_input: str, ai_response: str, user_id: str = "default_user", metadata: Dict[str, Any] = None):
        """
        记录交互。
        1. 存入短期缓冲 (这里简化为直接处理)
        2. 异步触发重要性分析
        """
        interaction_text = f"User: {user_input}\nAI: {ai_response}"
        
        # 异步触发分析与存储
        asyncio.create_task(self._analyze_and_save(interaction_text, user_id, metadata))

    async def _analyze_and_save(self, content: str, user_id: str, metadata: Dict[str, Any] = None):
        """
        分析交互重要性并决定是否存储为 EPISODIC 记忆
        """
        try:
            # 1. Importance Analysis via LLM
            system_prompt = (
                "You are a memory consolidation system. Analyze the following interaction between a User and an AI.\n"
                "Rate its importance for long-term memory on a scale of 0.0 to 1.0.\n"
                "Criteria for high importance:\n"
                "- Contains personal information about the user (name, preferences, location, job).\n"
                "- Represents a significant milestone or decision.\n"
                "- Contains specific facts that might be referenced later.\n"
                "Criteria for low importance:\n"
                "- Small talk (greetings, thanks).\n"
                "- Transient questions (what time is it).\n\n"
                "Output JSON only: {\"score\": float, \"reason\": \"string\"}"
            )
            
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=content)
            ])
            
            try:
                # 尝试解析 JSON，处理可能的 Markdown 包裹
                content_str = response.content.strip()
                if content_str.startswith("```json"):
                    content_str = content_str[7:-3]
                elif content_str.startswith("```"):
                    content_str = content_str[3:-3]
                
                analysis = json.loads(content_str)
                score = float(analysis.get("score", 0.0))
            except Exception as e:
                logger.warning(f"Failed to parse memory analysis result: {e}. Defaulting to score 0.0")
                score = 0.0

            # 2. If score > 0.7, save to Vector Store
            if score > 0.7:
                logger.info(f"💾 Saving important memory (Score: {score}): {analysis.get('reason')}")
                
                meta = metadata or {}
                meta["user_id"] = user_id
                meta["analysis_reason"] = analysis.get("reason")
                
                item = MemoryItem(
                    content=content,
                    type=MemoryType.EPISODIC,
                    importance_score=score,
                    metadata=meta
                )
                
                await self.storage.add_documents([item])
            else:
                logger.debug(f"Skipping low importance memory (Score: {score})")

        except Exception as e:
            logger.error(f"Error in _analyze_and_save: {e}")

    def _apply_time_decay_ranking(self, items: List[MemoryItem], top_k: int = 5) -> List[MemoryItem]:
        """
        Apply time decay to ranking:
        Adjusted Score = Similarity - (Decay_Penalty * (1 - Importance))
        Decay_Penalty = Days_Elapsed * 0.005 (0.5% per day)
        """
        now = datetime.utcnow()
        ranked_items = []
        
        for item in items:
            if item.similarity is None:
                # Fallback if no similarity score (shouldn't happen with vector search)
                final_score = item.importance_score
            else:
                days_elapsed = (now - item.timestamp).days
                days_elapsed = max(0, days_elapsed)
                
                # Decay Logic
                decay_penalty = days_elapsed * 0.005 
                # If importance is 1.0, penalty is 0. If importance is 0.0, penalty is full.
                penalty = decay_penalty * (1.0 - item.importance_score)
                
                final_score = item.similarity - penalty
            
            ranked_items.append((final_score, item))
            
        # Sort by final score desc
        ranked_items.sort(key=lambda x: x[0], reverse=True)
        
        return [item for _, item in ranked_items[:top_k]]

    async def retrieve_context(self, query: str, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Structured Hybrid Retrieval with Time Decay
        Returns:
            {
                "profile": ["User is ...", ...],
                "memories": ["[2023-01-01] ...", ...]
            }
        """
        try:
            # 1. Generate Query Vector
            query_vector = await self.embeddings.aembed_query(query)
            
            # 2. Parallel Search
            # Search Profile (No decay needed, usually few and high importance)
            profile_task = self.storage.search(
                query_vector=query_vector,
                limit=3,
                filter_dict={"type": MemoryType.USER_PROFILE.value, "user_id": user_id}
            )
            
            # Search Facts & History (Fetch more for pruning)
            facts_task = self.storage.search(
                query_vector=query_vector,
                limit=20, # Fetch 20 candidates for reranking
                filter_dict={"type": [MemoryType.SEMANTIC.value, MemoryType.EPISODIC.value], "user_id": user_id}
            )
            
            profile_items, fact_items = await asyncio.gather(profile_task, facts_task)
            
            # 3. Apply Time Decay Reranking to Facts
            final_fact_items = self._apply_time_decay_ranking(fact_items, top_k=5)
            
            # 4. Format Structured Output
            result = {
                "profile": [item.content for item in profile_items],
                "memories": [f"[{item.timestamp.strftime('%Y-%m-%d')}] {item.content}" for item in final_fact_items]
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in retrieve_context: {e}")
            return {"profile": [], "memories": []}

    async def update_user_profile(self, new_info: str, user_id: str = "default_user"):
        """
        显式更新用户画像
        """
        logger.info(f"Updating user profile for {user_id}: {new_info}")
        
        item = MemoryItem(
            content=new_info,
            type=MemoryType.USER_PROFILE,
            importance_score=1.0, # Explicit updates are always important
            metadata={"user_id": user_id, "source": "explicit_update"}
        )
        
        await self.storage.add_documents([item])

    async def add_semantic_knowledge(self, content: str, user_id: str = "default_user", metadata: Dict[str, Any] = None):
        """
        添加语义知识 (Facts)
        """
        meta = metadata or {}
        meta["user_id"] = user_id
        
        item = MemoryItem(
            content=content,
            type=MemoryType.SEMANTIC,
            importance_score=1.0,
            metadata=meta
        )
        await self.storage.add_documents([item])
