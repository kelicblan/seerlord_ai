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
from server.kernel.memory_manager import memory_manager

class SQLSkillManager:
    """
    Manages skills using PostgreSQL (Metadata/Code) and Qdrant (Vector Search).
    Replaces HierarchicalSkillManager's file-based storage.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SQLSkillManager, cls).__new__(cls)
            # No specific resource init needed if using shared memory_manager
            # But we rely on memory_manager being initialized elsewhere (server/main.py)
        return cls._instance

    async def initialize(self):
        """Ensure dependencies are ready."""
        # This might be called from main startup
        pass

    async def add_skill(self, skill: HierarchicalSkill, tenant_id: str, user_id: str = None):
        """
        Save a skill to Postgres and Qdrant.
        """
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

            # 2. Save to Qdrant (via MemoryManager)
            # We use a specific metadata type to distinguish skills from normal memories
            if memory_manager.enabled:
                content_text = f"{skill.name}: {skill.description}"
                metadata = {
                    "type": "skill",
                    "skill_id": skill.id,
                    "name": skill.name,
                    "level": skill.level.value,
                    # tenant_id is added by save_experience automatically
                }
                if user_id:
                    metadata["user_id"] = user_id
                
                # We use a fixed session_id for skills to group them logically, 
                # though tenant_id is the real boundary.
                await memory_manager.save_experience(
                    content=content_text,
                    agent_name="system_skill_manager",
                    session_id="global_skills_repo",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    metadata=metadata
                )
                
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
        if not memory_manager.enabled:
            return HierarchicalSkill(
                name="default_meta_skill",
                description="Memory disabled, returning default.",
                level=SkillLevel.META,
                content=SkillContent(code_logic="pass")
            ), "Memory Disabled"

        try:
            # 1. Search in Qdrant
            # We search specifically for skills in the "global_skills_repo" session
            candidates = await memory_manager.retrieve_relevant(
                query=query, 
                tenant_id=tenant_id,
                user_id=user_id,
                agent_name=agent_name,
                k=3,
                threshold=min_score
            )
            
            skill_ids = []
            for c in candidates:
                meta = c.get("metadata", {})
                if meta.get("type") == "skill" and "skill_id" in meta:
                    skill_ids.append(meta["skill_id"])
            
            if not skill_ids:
                return self._get_default_meta_skill(), "Fallback (No Skill Found)"

            # 2. Fetch from SQL
            db = SessionLocal()
            skills_map = {}
            try:
                db_skills = db.query(SkillModel).filter(SkillModel.id.in_(skill_ids)).all()
                for s in db_skills:
                    skills_map[s.id] = s
            finally:
                db.close()
                
            # 3. Reconstruct and Rank
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
