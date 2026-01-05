from typing import List, Optional
from pydantic import BaseModel, Field

class ComicPanel(BaseModel):
    """
    A single panel within a comic page (e.g., one of the 4 grids).
    """
    panel_number: int = Field(..., description="The panel number on the page (1-4).")
    image_prompt: str = Field(..., description="The detailed image generation prompt for this panel. MUST include the character visual description.")
    dialogue: str = Field(..., description="The text content (dialogue/caption) to be displayed in this panel.")

class ComicPage(BaseModel):
    """
    A full page of the comic book, containing multiple panels.
    """
    page_number: int = Field(..., description="The page number in the book.")
    title: str = Field(..., description="The title or question for this specific page.")
    description: Optional[str] = Field(None, description="Introductory text or context for this page.")
    panels: List[ComicPanel] = Field(..., description="List of 4 panels for this page.")

class ComicBook(BaseModel):
    """
    The structure of the generated comic book.
    """
    title: str = Field(..., description="The title of the comic book.")
    topic: str = Field(..., description="The main topic.")
    target_audience: str = Field(..., description="Target audience.")
    pages: List[ComicPage] = Field(..., description="The pages of the comic book.")
    character_description: Optional[str] = Field(None, description="Consistent visual description of the main character(s) to be used in all prompts")

class SyllabusPage(BaseModel):
    page_number: int = Field(..., description="Page number")
    title: str = Field(..., description="Title/Theme of the page")
    key_points: List[str] = Field(..., description="Key knowledge points to cover in this page")
    visual_metaphor: str = Field(..., description="Suggested visual metaphor for this page")

class CourseSyllabus(BaseModel):
    topic: str = Field(..., description="The user's requested topic")
    target_audience: str = Field(..., description="Target audience (e.g., children, engineers)")
    core_metaphor: str = Field(..., description="The central metaphor used throughout the course")
    outline: List[SyllabusPage] = Field(..., description="Page-by-page outline")
