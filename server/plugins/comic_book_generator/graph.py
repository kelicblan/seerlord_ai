from typing import Dict, Any, List
import uuid
import asyncio
from pathlib import Path
from loguru import logger

from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.callbacks.manager import adispatch_custom_event

from server.core.llm import get_llm
from server.memory.tools import memory_node
from server.models.artifact import AgentArtifact
from server.core.database import SessionLocal

from .state import ComicState
from .schema import ComicBook
from .tools import generate_image_base64, save_local_image, compose_comic_page, create_pdf_from_images

def analyze_request(state: ComicState):
    """
    Pass-through node to analyze intent.
    """
    return {"messages": [SystemMessage(content="Analyzing request for comic book generation...")]}

async def generate_storyboard(state: ComicState):
    """
    Generate the comic book script/storyboard.
    """
    messages = state.get("messages", [])
    last_user_msg = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    query = last_user_msg.content if last_user_msg else "Generate a comic book"

    llm = get_llm(temperature=0.7)
    structured_llm = llm.with_structured_output(ComicBook)
    
    prompt = f"""You are an expert comic book creator.
    
    User Request: {query}
    
    Goal: Create a multi-page comic book script.
    
    Structure:
    - Create 2-4 pages.
    - Each page MUST contain EXACTLY 4 panels (2x2 grid layout).
    - Provide a Title and Description for each page.
    
    For each Panel:
    - `image_prompt`: Detailed visual description in English. Style: "Comic book style, modern flat illustration".
    - `dialogue`: Short, punchy dialogue or caption to be displayed in the panel.
    """
    
    try:
        comic_book = await structured_llm.ainvoke([SystemMessage(content=prompt)])
        return {
            "comic_script": comic_book,
            "messages": [AIMessage(content=f"Generated storyboard: {comic_book.title}")]
        }
    except Exception as e:
        logger.error(f"Failed to generate storyboard: {e}")
        return {
            "messages": [AIMessage(content="Failed to generate comic storyboard. Please try again.")]
        }

async def generate_assets(state: ComicState):
    """
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

    async def _process_panel(page_num, panel):
        try:
            # Generate Image
            b64_img = await generate_image_base64.ainvoke(panel.image_prompt)
            if b64_img:
                # Save to disk
                suffix = f"_p{page_num}_pn{panel.panel_number}"
                local_path = save_local_image(b64_img, user_id, suffix)
                return page_num, panel.panel_number, local_path
        except Exception as e:
            logger.error(f"Failed to generate image for page {page_num} panel {panel.panel_number}: {e}")
        return page_num, panel.panel_number, None

    # Run in parallel (limit concurrency if needed, but for now full parallel)
    tasks = [_process_panel(p_num, p) for p_num, p in all_panels]
    results = await asyncio.gather(*tasks)
    
    for page_num, panel_num, path in results:
        if path:
            if page_num not in image_map:
                image_map[page_num] = {}
            image_map[page_num][panel_num] = path
            
    # We store this map in state, but state.image_map definition was Dict[int, str].
    # Let's just pass it to the next step via context or redefine state type.
    # For simplicity, we'll store it in a compatible way or update the node return.
    # The state definition is TypedDict, we can just return what we need.
    return {"image_map": image_map}

async def synthesize_pages(state: ComicState):
    """
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
        safe_user_id = "".join(ch for ch in (user_id or "unknown") if ch.isalnum() or ch in {"-", "_"})
        comic_dir = Path.cwd() / "server" / "data" / "user_files" / safe_user_id / "comics"
        comic_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_filename = f"comic_book_{uuid.uuid4()}.pdf"
        pdf_path = comic_dir / pdf_filename
        
        create_pdf_from_images(final_pages, str(pdf_path))
        
        # Save artifact for the PDF
        relative_path = Path(pdf_path).relative_to(Path.cwd() / "server" / "data" / "user_files")
        
        async with SessionLocal() as session:
            session.add(
                AgentArtifact(
                    id=str(uuid.uuid4()),
                    tenant_id=state.get("tenant_id") or "default",
                    user_id=user_id,
                    agent_id="comic_book_generator",
                    type="file",
                    value=str(relative_path),
                    title=f"{comic_book.title} (PDF)",
                    description=f"Full comic book PDF: {comic_book.topic}"
                )
            )
            await session.commit()
            
        msg = f"Comic book generated successfully: **{comic_book.title}**\n\n"
        msg += f"Saved as PDF: {relative_path}\n"
        
        return {
            "pdf_file_path": str(relative_path),
            "messages": [AIMessage(content=msg)]
        }
        
    except Exception as e:
        logger.error(f"Failed to create PDF: {e}")
        return {"messages": [AIMessage(content=f"Failed to create PDF: {e}")]}

# Graph Definition
comic_graph = StateGraph(ComicState)

comic_graph.add_node("memory_load", memory_node)
comic_graph.add_node("analyze_request", analyze_request)
comic_graph.add_node("generate_storyboard", generate_storyboard)
comic_graph.add_node("generate_assets", generate_assets)
comic_graph.add_node("synthesize_pages", synthesize_pages)

comic_graph.set_entry_point("memory_load")

comic_graph.add_edge("memory_load", "analyze_request")
comic_graph.add_edge("analyze_request", "generate_storyboard")
comic_graph.add_edge("generate_storyboard", "generate_assets")
comic_graph.add_edge("generate_assets", "synthesize_pages")
comic_graph.add_edge("synthesize_pages", END)

app = comic_graph.compile()
