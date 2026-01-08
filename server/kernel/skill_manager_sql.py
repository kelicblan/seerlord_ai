import json
import uuid
from typing import List, Optional, Tuple, Dict
from loguru import logger
from sqlalchemy import select, delete
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from server.core.config import settings
from server.core.database import SessionLocal
from server.db.models import Skill as SkillModel, SkillLevelEnum, SkillHistory
from server.kernel.hierarchical_skills import HierarchicalSkill, SkillLevel, SkillContent, GLOBAL_SKILL_TENANT_ID
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

    async def add_skill(self, skill: HierarchicalSkill, tenant_id: str, user_id: str = None, change_reason: str = "Manual Update"):
        """
        Save a skill to Postgres and Qdrant.
        Supports versioning: if skill exists, save snapshot to SkillHistory before update.
        """
        if not self.storage: await self.initialize()

        async with SessionLocal() as db:
            try:
                # 1. Save to PostgreSQL
                # Check if exists by ID
                result = await db.execute(select(SkillModel).where(SkillModel.id == skill.id))
                existing = result.scalars().first()

                # If not found by ID, check by Name (Deduplication)
                if not existing:
                    # Ignore tenant_id, search globally by name
                    name_check = await db.execute(select(SkillModel).where(
                        SkillModel.name == skill.name
                    ))
                    existing_by_name = name_check.scalars().first()
                    
                    if existing_by_name:
                        logger.warning(f"Skill with name '{skill.name}' already exists (ID: {existing_by_name.id}). Merging/Updating instead of creating duplicate.")
                        existing = existing_by_name
                        # Update the input skill object's ID to match the existing one
                        # This ensures Qdrant updates the correct vector instead of creating a new one
                        skill.id = existing.id
                
                if existing:
                    logger.info(f"Skill {skill.name} already exists (ID: {existing.id}), creating history snapshot and updating...")
                    
                    # Create History Snapshot
                    current_version = existing.version or 1
                    history_entry = SkillHistory(
                        id=str(uuid.uuid4()),
                        skill_id=existing.id,
                        version=current_version,
                        pre_content_json=existing.content_json,
                        change_description=change_reason,
                        agent_id=user_id or "system",
                        # created_at is auto
                    )
                    db.add(history_entry)
                    
                    # Update Existing
                    existing.name = skill.name
                    existing.description = skill.description
                    existing.code = skill.content.code_logic
                    existing.level = skill.level.value
                    existing.content_json = skill.model_dump(mode='json')
                    existing.version = current_version + 1
                    
                else:
                    new_skill = SkillModel(
                        id=skill.id,
                        name=skill.name,
                        description=skill.description,
                        code=skill.content.code_logic,
                        level=skill.level.value,
                        content_json=skill.model_dump(mode='json'),
                        tenant_id=tenant_id,
                        is_verified=False,
                        version=1
                    )
                    db.add(new_skill)
                
                await db.commit()

                # 2. Save to Qdrant (via VectorStoreManager)
                # We use a specific metadata type to distinguish skills from normal memories
                content_text = f"{skill.name}: {skill.description}"
                metadata = {
                    "type": MemoryType.SKILL.value,
                    "skill_id": skill.id,
                    "name": skill.name,
                    "level": skill.level.value,
                    "tenant_id": GLOBAL_SKILL_TENANT_ID # Force GLOBAL for vector store
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
                await db.rollback()

    async def delete_skill(self, skill_id: str):
        """
        Delete a skill from Postgres and Qdrant.
        """
        if not self.storage: await self.initialize()

        async with SessionLocal() as db:
            try:
                # 1. Delete from PostgreSQL
                result = await db.execute(select(SkillModel).where(SkillModel.id == skill_id))
                skill = result.scalars().first()
                if skill:
                    await db.delete(skill)
                    await db.commit()
                    logger.info(f"Deleted skill {skill_id} from SQL")
                else:
                    logger.warning(f"Skill {skill_id} not found in SQL")

                # 2. Delete from Qdrant
                # We need to find the Qdrant Point ID. 
                # We can use scroll with filter.
                filter_dict = {"skill_id": skill_id, "type": MemoryType.SKILL.value}
                points = await self.storage.scroll(limit=100, filter_dict=filter_dict)
                
                for point in points:
                    await self.storage.delete_by_id(point.id)
                    logger.info(f"Deleted skill vector {point.id} (skill_id={skill_id}) from Qdrant")

            except Exception as e:
                logger.error(f"Failed to delete skill {skill_id}: {e}")
                await db.rollback()

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
            # REMOVED tenant_id filter completely to search ALL skills
            candidates = await self.storage.search(
                query_vector=query_vector, 
                limit=3,
                score_threshold=min_score,
                filter_dict={"type": MemoryType.SKILL.value}
            )
            
            skill_ids = []
            for item in candidates:
                meta = item.metadata
                if "skill_id" in meta:
                    skill_ids.append(meta["skill_id"])
            
            if not skill_ids:
                return self._get_default_meta_skill(), "Fallback (No Skill Found)"

            # 3. Fetch from SQL
            skills_map = {}
            async with SessionLocal() as db:
                try:
                    result = await db.execute(select(SkillModel).where(SkillModel.id.in_(skill_ids)))
                    db_skills = result.scalars().all()
                    for s in db_skills:
                        skills_map[s.id] = s
                except Exception as e:
                    logger.error(f"Failed to fetch skills from SQL: {e}")
                
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
            return self._get_default_meta_skill(), f"Error: {e}"

    async def retrieve_related_skills(self, query: str, tenant_id: str, limit: int = 5, score_threshold: float = 0.6) -> List[HierarchicalSkill]:
        """
        Retrieve top-k related skills without fallback or default logic.
        """
        if not self.storage: await self.initialize()

        try:
            query_vector = await self.embeddings.aembed_query(query)
            # Force GLOBAL tenant search (Actually removing tenant filter)
            candidates = await self.storage.search(
                query_vector=query_vector, 
                limit=limit,
                score_threshold=score_threshold,
                filter_dict={"type": MemoryType.SKILL.value}
            )
            
            skill_ids = [item.metadata["skill_id"] for item in candidates if "skill_id" in item.metadata]
            if not skill_ids:
                return []

            results = []
            async with SessionLocal() as db:
                try:
                    result = await db.execute(select(SkillModel).where(SkillModel.id.in_(skill_ids)))
                    db_skills = result.scalars().all()
                    skill_map = {s.id: s for s in db_skills}
                    
                    # Preserve rank order
                    for sid in skill_ids:
                        if sid in skill_map:
                            try:
                                obj = HierarchicalSkill.model_validate(skill_map[sid].content_json)
                                results.append(obj)
                            except:
                                continue
                except Exception as e:
                    logger.error(f"Failed to fetch related skills: {e}")
                
            return results
        except Exception as e:
            logger.error(f"Related skills retrieval failed: {e}")
            return []

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
