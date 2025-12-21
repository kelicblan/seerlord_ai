from fastapi import APIRouter, HTTPException
from typing import List, Optional
from server.kernel.skill_service import skill_service, Skill, SkillEvolutionRecord

router = APIRouter()

@router.get("/", response_model=List[Skill])
async def get_skills(category: Optional[str] = None):
    """Get all skills, optionally filtered by category."""
    if category:
        return skill_service.get_skills_by_category(category)
    return skill_service.skills

@router.get("/{skill_id}", response_model=Skill)
async def get_skill(skill_id: str):
    """Get a specific skill by ID."""
    skill = skill_service.get_skill_by_id(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill

@router.get("/{skill_id}/history", response_model=List[SkillEvolutionRecord])
async def get_skill_history(skill_id: str):
    """Get evolution history for a specific skill."""
    skill = skill_service.get_skill_by_id(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill.history
