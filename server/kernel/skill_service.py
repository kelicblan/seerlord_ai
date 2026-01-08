from typing import List, Optional, Union
from loguru import logger
from pydantic import BaseModel, Field
import uuid
from datetime import datetime
from sqlalchemy import select

from server.kernel.hierarchical_skills import HierarchicalSkill, SkillContent, SkillLevel, GLOBAL_SKILL_TENANT_ID
from server.kernel.dynamic_skill_manager import dynamic_skill_manager
from server.core.database import SessionLocal
from server.db.models import Skill as SkillModel, SkillHistory

# --- Legacy Data Models (For API Backward Compatibility) ---

class SkillEvolutionRecord(BaseModel):
    """Record of a single evolution/update event for a skill."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    skill_id: str
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp() * 1000)
    agent_id: str  # Which agent triggered this
    change_description: str
    diff: Optional[str] = None
    version: int
    snapshot_content: Optional[str] = None # Added for frontend display

class SkillCreate(BaseModel):
    """Schema for creating a new skill."""
    name: str
    description: str = ""
    category: str = "general"
    level: int = 1  # 1: Specific, 2: Domain, 3: Meta
    parentId: Optional[str] = None
    content: str = "" # The Prompt/Instruction
    tags: List[str] = []

class Skill(SkillCreate):
    """API Schema for Skill (Legacy Format)"""
    id: str
    history: List[SkillEvolutionRecord] = []
    version: int = 1

# --- Service ---

class SkillService:
    """
    Facade for the Skill System.
    Connects to DynamicSkillManager (Real DB + Evolution) and provides legacy API support.
    """
    def __init__(self):
        self.manager = dynamic_skill_manager

    @property
    async def skills(self) -> List[Skill]:
        """
        Legacy property to get all skills.
        Fetches from DB and converts to legacy schema.
        """
        async with SessionLocal() as db:
            try:
                # No longer filtering by tenant, treating all as global/shared
                result = await db.execute(select(SkillModel))
                db_skills = result.scalars().all()
                return [self._convert_to_legacy_skill(s) for s in db_skills]
            except Exception as e:
                logger.error(f"Failed to fetch all skills: {e}")
                return []

    async def get_skills_by_category(self, category: str) -> List[Skill]:
        """Legacy method to filter skills."""
        # Note: 'skills' is now async property
        all_skills = await self.skills
        if category == "all":
            return all_skills
        return [s for s in all_skills if category in s.tags or category in s.name.lower()]

    async def get_skill_by_id(self, skill_id: str) -> Optional[Skill]:
        """Legacy method to get skill by ID."""
        async with SessionLocal() as db:
            try:
                result = await db.execute(
                    select(SkillModel).where(
                        SkillModel.id == skill_id
                    )
                )
                db_skill = result.scalars().first()
                if db_skill:
                    return self._convert_to_legacy_skill(db_skill)
                return None
            except Exception as e:
                logger.error(f"Failed to fetch skill {skill_id}: {e}")
                return None

    async def get_skill_history(self, skill_id: str) -> List[SkillEvolutionRecord]:
        """Get skill history from DB."""
        async with SessionLocal() as db:
            try:
                # Retrieve from SkillHistory table
                # We also need the current version from Skill table to show complete timeline if needed, 
                # but SkillHistory contains PAST versions.
                # The frontend expects a list of records.
                
                result = await db.execute(
                    select(SkillHistory)
                    .where(SkillHistory.skill_id == skill_id)
                    .order_by(SkillHistory.created_at.desc())
                )
                history_entries = result.scalars().all()
                
                records = []
                for h in history_entries:
                    # Extract prompt_template from pre_content_json if available
                    snapshot_text = "N/A"
                    if h.pre_content_json:
                         # Handle different structures
                         if "content" in h.pre_content_json and isinstance(h.pre_content_json["content"], dict):
                             snapshot_text = h.pre_content_json["content"].get("prompt_template", "")
                         elif "prompt_template" in h.pre_content_json:
                             snapshot_text = h.pre_content_json["prompt_template"]
                         else:
                             # Fallback to dumping whole json if structure is weird
                             import json
                             snapshot_text = json.dumps(h.pre_content_json, indent=2, ensure_ascii=False)

                    records.append(SkillEvolutionRecord(
                        id=h.id,
                        skill_id=h.skill_id,
                        timestamp=h.created_at.timestamp() * 1000 if h.created_at else 0,
                        agent_id=h.agent_id or "unknown",
                        change_description=h.change_description or "Update",
                        diff=None, # Diff calculation not implemented yet
                        version=h.version,
                        snapshot_content=snapshot_text
                    ))
                return records
            except Exception as e:
                logger.error(f"Failed to fetch history for {skill_id}: {e}")
                return []

    async def delete_skill(self, skill_id: str) -> bool:
        """Delete a skill."""
        try:
            await self.manager.skill_manager.delete_skill(skill_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete skill {skill_id}: {e}")
            return False

    async def create_skill(self, skill_data: Union[Skill, SkillCreate]) -> bool:
        """Create a new skill from legacy format."""
        # Convert Legacy Skill -> HierarchicalSkill
        level_map_rev = {1: SkillLevel.SPECIFIC, 2: SkillLevel.DOMAIN, 3: SkillLevel.META}
        
        content = SkillContent(
            prompt_template=skill_data.content or "", # Ensure not None
            knowledge_base=[]
        )
        
        # Ensure ID is present if not provided
        if isinstance(skill_data, Skill):
             skill_id = skill_data.id
        else:
             skill_id = str(uuid.uuid4())

        h_skill = HierarchicalSkill(
            id=skill_id,
            name=skill_data.name,
            description=skill_data.description,
            level=level_map_rev.get(skill_data.level, SkillLevel.SPECIFIC),
            parent_id=skill_data.parentId,
            content=content,
            tags=skill_data.tags or []
        )
        
        try:
            # Force GLOBAL tenant for all skills (though technically we are removing distinction)
            # We still need to pass a tenant_id to DB, so we keep using GLOBAL_SKILL_TENANT_ID as the system default
            await self.manager.skill_manager.add_skill(h_skill, tenant_id=GLOBAL_SKILL_TENANT_ID)
            return True
        except Exception as e:
            logger.error(f"Failed to create skill: {e}")
            return False

    async def update_skill(self, skill_id: str, skill_data: Union[Skill, SkillCreate]) -> bool:
        """Update existing skill."""
        # If it's SkillCreate, we temporarily attach the ID to treat it like a full Skill update
        if isinstance(skill_data, SkillCreate):
             # Create a Skill object or just pass it to create_skill which handles it
             pass
        
        # Actually create_skill logic handles both now, but we need to ensure ID is set for update
        # For update, we want to preserve the ID.
        
        # Re-use create_skill logic but force the ID
        level_map_rev = {1: SkillLevel.SPECIFIC, 2: SkillLevel.DOMAIN, 3: SkillLevel.META}
        
        content = SkillContent(
            prompt_template=skill_data.content or "", 
            knowledge_base=[]
        )

        h_skill = HierarchicalSkill(
            id=skill_id,
            name=skill_data.name,
            description=skill_data.description,
            level=level_map_rev.get(skill_data.level, SkillLevel.SPECIFIC),
            parent_id=skill_data.parentId,
            content=content,
            tags=skill_data.tags or []
        )

        try:
            await self.manager.skill_manager.add_skill(h_skill, tenant_id=GLOBAL_SKILL_TENANT_ID) # add_skill handles upsert
            return True
        except Exception as e:
            logger.error(f"Failed to update skill: {e}")
            return False

    def _convert_to_legacy_skill(self, db_skill: SkillModel) -> Skill:
        """Helper to convert DB model to Pydantic Legacy Skill."""
        content_data = db_skill.content_json or {}
        
        # Map levels: specific->1, domain->2, meta->3
        level_map = {"specific": 1, "domain": 2, "meta": 3}
        level_int = level_map.get(db_skill.level, 1)
        
        # Extract content prompt
        prompt = ""
        if "content" in content_data and isinstance(content_data["content"], dict):
             prompt = content_data["content"].get("prompt_template", "")
        elif "prompt_template" in content_data:
             prompt = content_data["prompt_template"]
        
        return Skill(
            id=db_skill.id,
            name=db_skill.name,
            description=db_skill.description or "",
            category="general", # Default
            level=level_int,
            parentId=content_data.get("parent_id"),
            content=prompt,
            tags=content_data.get("tags", []),
            history=[], # Evolution history not fully migrated to this view yet
            version=1
        )

    async def retrieve_skills_for_query(self, query: str, category: str = None, tenant_id: str = "default", user_id: str = None, agent_description: str = "") -> List[HierarchicalSkill]:
        """
        Retrieves skills using the real DynamicSkillManager.
        This includes automatic evolution if no specific skills are found.
        """
        try:
            # 1. Ensure we have at least one good skill (triggers evolution if needed)
            # Use GLOBAL_SKILL_TENANT_ID for retrieval
            best_skill, reason = await self.manager.get_or_evolve_skill(
                query, 
                tenant_id=GLOBAL_SKILL_TENANT_ID, 
                user_id=user_id,
                agent_description=agent_description
            )
            
            # 2. Get related skills (Context expansion)
            related = await self.manager.skill_manager.retrieve_related_skills(query, tenant_id=GLOBAL_SKILL_TENANT_ID, limit=5)
            
            # 3. Merge and deduplicate
            skills_map = {s.id: s for s in related}
            skills_map[best_skill.id] = best_skill 
            
            final_list = list(skills_map.values())
            
            logger.info(f"SkillService retrieved {len(final_list)} skills for '{query}' (Triggered by: {reason})")
            return final_list
            
        except Exception as e:
            logger.error(f"SkillService failed: {e}")
            return []

# Singleton Instance
skill_service = SkillService()
