from fastapi import APIRouter, HTTPException
from typing import List, Optional
from server.kernel.skill_service import skill_service, Skill, SkillEvolutionRecord, SkillCreate

router = APIRouter()

@router.get("", response_model=List[Skill])
async def get_skills(category: Optional[str] = None):
    """Get all skills, optionally filtered by category."""
    if category:
        return await skill_service.get_skills_by_category(category)
    return await skill_service.skills

@router.post("", response_model=Skill)
async def create_skill(skill: SkillCreate):
    """Create a new skill."""
    import uuid
    new_id = str(uuid.uuid4())
    
    # Construct full Skill object with generated ID to pass to service and return to client
    full_skill = Skill(id=new_id, **skill.dict())
    
    success = await skill_service.create_skill(full_skill)
    
    if success:
        return full_skill
    else:
        raise HTTPException(status_code=500, detail="Failed to create skill")

@router.get("/{skill_id}", response_model=Skill)
async def get_skill(skill_id: str):
    """Get a specific skill by ID."""
    skill = await skill_service.get_skill_by_id(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill

@router.get("/{skill_id}/history", response_model=List[SkillEvolutionRecord])
async def get_skill_history(skill_id: str):
    """Get evolution history for a specific skill."""
    # Use the new service method
    return await skill_service.get_skill_history(skill_id)

@router.delete("/{skill_id}")
async def delete_skill(skill_id: str):
    """Delete a skill."""
    skill = await skill_service.get_skill_by_id(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    success = await skill_service.delete_skill(skill_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete skill")
    
    return {"message": "Skill deleted successfully"}

@router.put("/{skill_id}", response_model=Skill)
async def update_skill(skill_id: str, skill: SkillCreate):
    """Update an existing skill."""
    existing = await skill_service.get_skill_by_id(skill_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Skill not found")
        
    success = await skill_service.update_skill(skill_id, skill)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update skill")
    
    # Return updated object
    # Construct it from input + id
    return Skill(id=skill_id, **skill.dict())

