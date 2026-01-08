from typing import Dict, Any, List
import uuid
import asyncio
from pathlib import Path
from loguru import logger

from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.callbacks.manager import adispatch_custom_event

from server.core.llm import get_llm
from server.models.artifact import AgentArtifact
from server.core.database import SessionLocal
from server.kernel.skill_integration import skill_injector
from server.memory.tools import memory_node

from .state import ComicState
from .schema import ComicBook, CourseSyllabus
from .tools import generate_image_base64, save_local_image, compose_comic_page, create_pdf_from_images

def analyze_request(state: ComicState):
    """
    Pass-through node to analyze intent.
    """
    return {"messages": [SystemMessage(content="Analyzing request for comic book generation...")]}

async def generate_syllabus(state: ComicState):
    """
    Stage 1: Curriculum Designer (The Teacher)
    Generate a structured syllabus based on user intent.
    """
    messages = state.get("messages", [])
    last_user_msg = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    query = last_user_msg.content if last_user_msg else "Generate a comic book"
    
    llm = get_llm(temperature=0.7)
    structured_llm = llm.with_structured_output(CourseSyllabus)
    
    skills = state.get("skills_context", "")
    memory_context = state.get("memory_context", "")
    
    prompt = f"""You are an expert Curriculum Designer (The Teacher) for a "Comic Learning Course".
    
    User Request: {query}
    
    [Memory Context]:
    {memory_context}
    
    [Expert Skills & Guidelines]:
    {skills}
    
    Your Goal: Transform this vague intent into a structured teaching syllabus.
    
    Tasks:
    1. Identify the Target Audience (e.g., "5-year-old kids", "Software Engineers", "General Public").
    2. Create a Core Metaphor (e.g., "Quantum Entanglement" -> "Magic Twin Cats").
    3. Outline 2-4 Pages. Each page must have a clear "Key Knowledge Point" and a "Visual Metaphor".
    
    Output structured JSON matching the CourseSyllabus schema.
    """
    
    try:
        syllabus = await structured_llm.ainvoke([SystemMessage(content=prompt)])
        return {
            "syllabus": syllabus,
            "messages": [AIMessage(content=f"Generated Syllabus: {syllabus.topic} for {syllabus.target_audience}")]
        }
    except Exception as e:
        logger.error(f"Failed to generate syllabus: {e}")
        return {
            "messages": [AIMessage(content="Failed to generate syllabus. Please try again.")]
        }

async def generate_storyboard(state: ComicState):
    """
    Stage 2: Scriptwriter (The Director)
    Generate the comic book script/storyboard from the syllabus.
    """
    syllabus = state.get("syllabus")
    if not syllabus:
        return {"messages": [AIMessage(content="Missing syllabus. Cannot generate storyboard.")]}
        
    llm = get_llm(temperature=0.7)
    structured_llm = llm.with_structured_output(ComicBook)
    
    skills = state.get("skills_context", "")
    
    prompt = f"""You are an expert Comic Book Director and Scriptwriter.
    
    [Expert Skills & Guidelines]:
    {skills}
    
    Input Syllabus:
    Topic: {syllabus.topic}
    Audience: {syllabus.target_audience}
    Core Metaphor: {syllabus.core_metaphor}
    Outline: {syllabus.outline}
    
    Your Goal: Create a detailed comic book script.
    
    CRITICAL REQUIREMENT - CHARACTER CONSISTENCY:
    1. Define a "Main Character" visually. (e.g., "A cute blue robot with round yellow eyes and a red antenna").
    2. Write this description into the `character_description` field.
    3. IMPORTANT: You MUST prepend this exact character description to EVERY `image_prompt` in every panel. 
       Example: "A cute blue robot with round yellow eyes... [rest of the scene description]"
    
    Structure:
    - Create exactly {len(syllabus.outline)} pages (matching the syllabus).
    - Each page MUST contain EXACTLY 4 panels (2x2 grid layout).
    
    For each Panel:
    - `image_prompt`: detailed visual description (start with character description).
    - `dialogue`: Short, punchy dialogue.
    """
    
    try:
        comic_book = await structured_llm.ainvoke([SystemMessage(content=prompt)])
        return {
            "comic_script": comic_book,
            "messages": [AIMessage(content=f"Generated Storyboard: {comic_book.title}")]
        }
    except Exception as e:
        logger.error(f"Failed to generate storyboard: {e}")
        return {
            "messages": [AIMessage(content="Failed to generate comic storyboard. Please try again.")]
        }

async def generate_assets(state: ComicState):
    """
    Stage 3: Illustrator (The Artist)
    Generate images for each panel in each page.
    """
    comic_book = state.get("comic_script")
    if not comic_book:
        return {}
    
    user_id = state.get("user_id")
    # Map: page_num -> { panel_num -> image_path }
    image_map: Dict[int, Dict[int, str]] = {}
    
    all_panels = []
    for page in comic_book.pages:
        for panel in page.panels:
            all_panels.append((page.page_number, panel))

    # Send progress event
    await adispatch_custom_event(
        "comic_generation_progress",
        {"status": "start_image_generation", "total_panels": len(all_panels)}
    )

    # Limit concurrency to 2 to avoid rate limits (429 Throttling)
    # Most trial/tier-1 keys have low QPS limits.
    semaphore = asyncio.Semaphore(2)

    async def _process_panel(page_num, panel):
        async with semaphore:
            # Add a small delay to further respect QPS
            await asyncio.sleep(2.0)
            try:
                # Generate Image
                # The prompt already includes the character description from the previous step
                b64_img = await generate_image_base64.ainvoke(panel.image_prompt)
                if b64_img:
                    # Save to disk
                    suffix = f"_p{page_num}_pn{panel.panel_number}"
                    local_path = save_local_image(b64_img, user_id, suffix)
                    return page_num, panel.panel_number, local_path
            except Exception as e:
                logger.error(f"Failed to generate image for page {page_num} panel {panel.panel_number}: {e}")
            return page_num, panel.panel_number, None

    # Run in parallel
    tasks = [_process_panel(p_num, p) for p_num, p in all_panels]
    results = await asyncio.gather(*tasks)
    
    for page_num, panel_num, path in results:
        if path:
            if page_num not in image_map:
                image_map[page_num] = {}
            image_map[page_num][panel_num] = path
            
    return {"image_map": image_map}

from server.core.storage import s3_client

async def synthesize_pages(state: ComicState):
    """
    Stage 4: Typesetter (The Publisher)
    Compose final page images using Pillow and stitch into PDF.
    """
    comic_book = state.get("comic_script")
    image_map = state.get("image_map") 
    user_id = state.get("user_id")
    
    if not comic_book:
        return {}

    final_pages = []
    
    # 1. Compose each page image
    for page in comic_book.pages:
        page_images = image_map.get(page.page_number, {})
        try:
            # Compose the page
            page_img_path = compose_comic_page(page, page_images, user_id)
            final_pages.append(page_img_path)
        except Exception as e:
            logger.error(f"Failed to compose page {page.page_number}: {e}")

    if not final_pages:
         return {"messages": [AIMessage(content="Failed to generate any comic pages.")]}

    # 2. Create PDF from pages
    try:
        # Use temp directory for initial PDF creation
        temp_dir = (Path.cwd() / "server" / "data" / "temp" / "comics").resolve()
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_filename = f"comic_book_{uuid.uuid4()}.pdf"
        pdf_path = temp_dir / pdf_filename
        
        create_pdf_from_images(final_pages, str(pdf_path))
        
        safe_user_id = "".join(ch for ch in (user_id or "unknown") if ch.isalnum() or ch in {"-", "_"})
        artifact_value = None
        
        if s3_client.enabled:
            object_name = f"comics/{safe_user_id}/{pdf_filename}"
            s3_url = s3_client.upload_file(pdf_path, object_name)
            if s3_url:
                artifact_value = s3_url
                # Cleanup PDF from temp
                try:
                    os.remove(pdf_path)
                except:
                    pass
        
        if not artifact_value:
             # Fallback to local user_files
             local_dir = (Path.cwd() / "server" / "data" / "user_files" / safe_user_id / "comics").resolve()
             local_dir.mkdir(parents=True, exist_ok=True)
             final_local_path = local_dir / pdf_filename
             
             # Move from temp to local
             import shutil
             shutil.move(str(pdf_path), str(final_local_path))
             
             relative_path = str(final_local_path.relative_to(Path.cwd() / "server" / "data" / "user_files"))
             artifact_value = relative_path

        # Cleanup intermediate composed pages
        for p in final_pages:
             try:
                 if "temp" in p:
                     os.remove(p)
             except:
                 pass

        async with SessionLocal() as session:
            session.add(
                AgentArtifact(
                    id=str(uuid.uuid4()),
                    tenant_id=state.get("tenant_id") or "default",
                    user_id=user_id,
                    agent_id="comic_book_generator",
                    type="file",
                    value=artifact_value,
                    title=f"{comic_book.title} (PDF)",
                    description=f"Full comic book PDF: {comic_book.topic}"
                )
            )
            await session.commit()
            
        msg = f"Comic book generated successfully: **{comic_book.title}**\n\n"
        if artifact_value.startswith("http"):
             msg += f"Download PDF: [Click Here]({artifact_value})\n"
        else:
             msg += f"Saved as PDF: {artifact_value}\n"
        
        return {
            "pdf_file_path": artifact_value,
            "messages": [AIMessage(content=msg)]
        }
        
    except Exception as e:
        logger.error(f"Failed to create PDF: {e}")
        return {"messages": [AIMessage(content=f"Failed to create PDF: {e}")]}

# Graph Definition
comic_graph = StateGraph(ComicState)

comic_graph.add_node("load_skills", skill_injector.load_skills_context)
comic_graph.add_node("memory_load", memory_node)
comic_graph.add_node("analyze_request", analyze_request)
comic_graph.add_node("generate_syllabus", generate_syllabus)
comic_graph.add_node("generate_storyboard", generate_storyboard)
comic_graph.add_node("generate_assets", generate_assets)
comic_graph.add_node("synthesize_pages", synthesize_pages)

comic_graph.set_entry_point("load_skills")
comic_graph.add_edge("load_skills", "memory_load")
comic_graph.add_edge("memory_load", "analyze_request")

comic_graph.add_edge("analyze_request", "generate_syllabus")
comic_graph.add_edge("generate_syllabus", "generate_storyboard")
comic_graph.add_edge("generate_storyboard", "generate_assets")
comic_graph.add_edge("generate_assets", "synthesize_pages")
comic_graph.add_edge("synthesize_pages", END)

app = comic_graph.compile()
