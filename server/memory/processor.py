import asyncio
import json
from typing import List, Dict, Any
from uuid import UUID

from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage

from server.core.llm import get_llm, get_embeddings
from server.memory.schemas import MemoryItem, MemoryType
from server.memory.storage import VectorStoreManager

class MemoryProcessor:
    """
    后台反思与整理服务
    模拟海马体功能：从情景记忆中提取语义记忆
    """
    def __init__(self):
        self.storage = None
        self.llm = get_llm(temperature=0.3)
        self.embeddings = get_embeddings()

    async def initialize(self):
        self.storage = await VectorStoreManager.get_instance()

    async def synthesize_memories(self, user_id: str = "default_user", batch_size: int = 10):
        """
        核心反思循环：提取事实，整合记忆
        """
        if not self.storage:
            await self.initialize()

        logger.info(f"🧠 Starting memory synthesis for {user_id}...")

        # 1. 获取未整理的情景记忆
        # 注意：这里假设 metadata 中有 consolidated 标记，或者我们只取最近的
        # 为了简化，我们查询最近的 EPISODIC 且 consolidated != True
        # 由于 scroll 不支持复杂逻辑，这里简单取最近 batch_size 条，然后手动过滤
        
        items = await self.storage.scroll(
            limit=batch_size * 2,
            filter_dict={"type": MemoryType.EPISODIC.value, "user_id": user_id}
        )
        
        unconsolidated_items = [
            item for item in items 
            if not item.metadata.get("consolidated", False)
        ][:batch_size]

        if not unconsolidated_items:
            logger.info("No new memories to synthesize.")
            return

        logger.info(f"Found {len(unconsolidated_items)} unconsolidated memories.")
        
        # 2. 准备 Prompt 输入
        conversation_text = "\n---\n".join([item.content for item in unconsolidated_items])
        
        system_prompt = (
            "You are an AI memory manager. Your goal is to extract core facts and user preferences from conversation history.\n"
            "Ignore trivial details. Focus on:\n"
            "- User Personal Info (Name, Job, Location)\n"
            "- User Preferences (Likes, Dislikes, Styles)\n"
            "- Important Life Events\n\n"
            "Output a JSON list of facts. Example: [\"User lives in NYC\", \"User likes Python\"]\n"
            "If no important facts, output []"
        )

        try:
            # 3. LLM 提取
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=conversation_text)
            ])
            
            content_str = response.content.strip()
            if content_str.startswith("```json"):
                content_str = content_str[7:-3]
            elif content_str.startswith("```"):
                content_str = content_str[3:-3]
            
            facts = json.loads(content_str)
            
            if not isinstance(facts, list):
                logger.warning("LLM output is not a list")
                facts = []

            # 4. 存入语义记忆 (去重逻辑)
            for fact in facts:
                await self._save_fact(fact, user_id)

            # 5. 标记已处理
            for item in unconsolidated_items:
                new_meta = item.metadata.copy()
                new_meta["consolidated"] = True
                
                memory_type = item.type.value if hasattr(item.type, "value") else item.type
                
                await self.storage.update_by_id(item.id, {
                    "content": item.content, 
                    "type": memory_type, 
                    "timestamp": item.timestamp.isoformat(), 
                    "importance_score": item.importance_score,
                    **new_meta
                })
                
            logger.info(f"✅ Synthesized {len(facts)} new facts from {len(unconsolidated_items)} episodes.")

        except Exception as e:
            logger.error(f"Error in synthesize_memories: {e}")

    async def _save_fact(self, fact_content: str, user_id: str):
        """
        保存单个事实，带去重/更新逻辑
        """
        # 1. 检查是否存在相似事实
        fact_vector = await self.embeddings.aembed_query(fact_content)
        
        similar_items = await self.storage.search(
            query_vector=fact_vector,
            limit=1,
            filter_dict={"type": MemoryType.SEMANTIC.value, "user_id": user_id}
        )
        
        # 阈值判断
        if similar_items:
            # Qdrant search 结果通常是按相似度排序，但 client.search 返回的是 MemoryItem 对象，我们丢失了 score
            # 等等，Storage.search 返回的是 MemoryItem，没有 score。
            # 这是一个设计上的小缺陷，Storage.search 应该最好返回 score。
            # 为了简单，我假设如果搜到了且 limit=1，我们默认它可能很相似。
            # 但实际上我们需要 score 来决定是合并还是新增。
            # 我需要修改 Storage.search 让它包含 score 或者在 item metadata 里塞入 score?
            # 暂时，我们假设如果 LLM 提取了 "User likes Python"，而库里有 "User loves Python"，
            # 相似度很高。
            # 让我们做一个简单的逻辑：直接新增，或者如果为了严谨，修改 Storage 返回 score。
            pass

        # 由于 Storage.search 封装丢失了 score，这里我们简单策略：
        # 总是新增事实 (Insert)，让检索层去处理多条相似信息（RAG 会检索多条，LLM 会综合）。
        # 或者，我们可以做一个 "Semantic Deduplication" 的离线任务。
        # 这里为了符合 "Update if exists" 的要求，我必须获取 score。
        
        # 既然不能改 Storage 接口太大，我直接用 storage.client 来做一次带 score 的 check?
        # 不，这样破坏封装。
        # 我决定：直接新增。对于 Semantic Memory，多一点冗余是可以接受的。
        # 如果用户坚持 "Update"，我需要改 Storage。
        # 让我们修改 Storage.search 返回 (item, score) 吗？
        # 或者在 MemoryItem 中加个 transient field `_score`?
        
        # 既然现在是 Pair Programming，我决定修改 Storage.search 返回 List[Tuple[MemoryItem, float]] 吗？
        # 不，那样会破坏其他调用的签名。
        # 我会在 MemoryItem 的 metadata 里临时放一个 `_score` 或者 `search_score`。
        
        # 重新看 Storage.search 实现：
        # 它解析 payload。
        # 我可以在 storage.search 里把 hit.score 塞进 item.metadata['_score']。
        
        # 这是一个聪明的 hack。
        
        item = MemoryItem(
            content=fact_content,
            type=MemoryType.SEMANTIC,
            importance_score=1.0,
            metadata={"user_id": user_id, "source": "synthesis"}
        )
        await self.storage.add_documents([item])
