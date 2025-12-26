import json
import uuid
from typing import List, Optional, Tuple, Dict
from loguru import logger
from sqlalchemy.orm import Session
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from server.core.config import settings
from server.db.session import SessionLocal
from server.db.models import Skill as SkillModel, SkillLevelEnum
from server.kernel.hierarchical_skills import HierarchicalSkill, SkillLevel, SkillContent
from server.memory.storage import VectorStoreManager
from server.memory.schemas import MemoryItem, MemoryType
from server.core.llm import get_embeddings

class SQLSkillManager:
    """
    Manages skills using PostgreSQL (Metadata/Code) and Qdrant (Vector Search).
    Replaces HierarchicalSkillManager's file-based storage.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SQLSkillManager, cls).__new__(cls)
            cls._instance.storage = None
            cls._instance.embeddings = None
        return cls._instance

    async def initialize(self):
        """Ensure dependencies are ready."""
        self.storage = await VectorStoreManager.get_instance()
        self.embeddings = get_embeddings()

    async def add_skill(self, skill: HierarchicalSkill, tenant_id: str, user_id: str = None):
        """
        Save a skill to Postgres and Qdrant.
        """
        if not self.storage: await self.initialize()

        db = SessionLocal()
        try:
            # 1. Save to PostgreSQL
            # Check if exists
            existing = db.query(SkillModel).filter(SkillModel.id == skill.id).first()
            if existing:
                logger.info(f"Skill {skill.name} already exists, updating...")
                existing.name = skill.name
                existing.description = skill.description
                existing.code = skill.content.code_logic
                existing.level = skill.level.value
                existing.content_json = skill.model_dump(mode='json')
            else:
                new_skill = SkillModel(
                    id=skill.id,
                    name=skill.name,
                    description=skill.description,
                    code=skill.content.code_logic,
                    level=skill.level.value,
                    content_json=skill.model_dump(mode='json'),
                    tenant_id=tenant_id,
                    is_verified=False
                )
                db.add(new_skill)
            
            db.commit()

            # 2. Save to Qdrant (via VectorStoreManager)
            # We use a specific metadata type to distinguish skills from normal memories
            content_text = f"{skill.name}: {skill.description}"
            metadata = {
                "type": MemoryType.SKILL.value,
                "skill_id": skill.id,
                "name": skill.name,
                "level": skill.level.value,
                "tenant_id": tenant_id
            }
            if user_id:
                metadata["user_id"] = user_id
            
            item = MemoryItem(
                content=content_text,
                type=MemoryType.SKILL,
                importance_score=1.0,
                metadata=metadata
            )
            
            await self.storage.add_documents([item])
                
            logger.info(f"✅ Saved skill {skill.name} to SQL + Qdrant (Tenant: {tenant_id}, User: {user_id})")

        except Exception as e:
            logger.error(f"Failed to add skill: {e}")
            db.rollback()
        finally:
            db.close()

    async def retrieve_best_skill(self, query: str, tenant_id: str, user_id: str = None, agent_name: str = "system_skill_manager", min_score: float = 0.7) -> Tuple[Optional[HierarchicalSkill], str]:
        """
        Retrieve best skill using Vector Search -> SQL Lookup.
        """
        if not self.storage: await self.initialize()

        try:
            # 1. Generate Query Vector
            query_vector = await self.embeddings.aembed_query(query)

            # 2. Search in Qdrant
            # We search specifically for skills in the "global_skills_repo" session
            candidates = await self.storage.search(
                query_vector=query_vector, 
                limit=3,
                score_threshold=min_score,
                filter_dict={"type": MemoryType.SKILL.value, "tenant_id": tenant_id}
            )
            
            skill_ids = []
            for item in candidates:
                meta = item.metadata
                if "skill_id" in meta:
                    skill_ids.append(meta["skill_id"])
            
            if not skill_ids:
                return self._get_default_meta_skill(), "Fallback (No Skill Found)"

            # 3. Fetch from SQL
            db = SessionLocal()
            skills_map = {}
            try:
                db_skills = db.query(SkillModel).filter(SkillModel.id.in_(skill_ids)).all()
                for s in db_skills:
                    skills_map[s.id] = s
            finally:
                db.close()
                
            # 4. Reconstruct and Rank
            # Return the first one that was found in Qdrant (preserving rank order)
            for sid in skill_ids:
                if sid in skills_map:
                    db_skill = skills_map[sid]
                    try:
                        skill_obj = HierarchicalSkill.model_validate(db_skill.content_json)
                        return skill_obj, f"Vector Match ({db_skill.level})"
                    except Exception as e:
                        logger.error(f"Error hydrating skill {sid}: {e}")
                        continue
                        
            return self._get_default_meta_skill(), "Fallback (DB Sync Error)"

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return None, f"Error: {e}"

    def _get_default_meta_skill(self) -> HierarchicalSkill:
        """Return a basic meta skill if nothing found."""
        return HierarchicalSkill(
            name="GeneralProblemSolver",
            description="Decomposes the problem and solves it step-by-step.",
            level=SkillLevel.META,
            content=SkillContent(
                prompt_template="Solve this: {task}",
                knowledge_base=["Think step by step."]
            )
        )
