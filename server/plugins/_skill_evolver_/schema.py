from pydantic import BaseModel, Field

class EvolutionSchema(BaseModel):
    skill_name: str = Field(description="Name of the evolved skill")
    reasoning: str = Field(description="Why this skill was evolved")
