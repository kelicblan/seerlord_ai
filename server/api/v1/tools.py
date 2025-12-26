import os
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from server.kernel.mcp_manager import mcp_manager
from loguru import logger

router = APIRouter()

class MdToPdfRequest(BaseModel):
    content: str

@router.post("/tools/md_to_pdf")
async def md_to_pdf(request: MdToPdfRequest, background_tasks: BackgroundTasks):
    """
    Convert Markdown content to PDF using the 'mdtofiles' MCP server.
    """
    # 1. Check if tool exists
    tool = mcp_manager.get_tool("mdtofiles", "md_to_pdf_tool")
    if not tool:
        raise HTTPException(status_code=503, detail="MD to PDF tool not available. Ensure 'mdtofiles' MCP server is running.")

    # 2. Create temp directory
    temp_dir = os.path.join(os.getcwd(), "server", "data", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    task_id = str(uuid.uuid4())
    md_filename = f"{task_id}.md"
    pdf_filename = f"{task_id}.pdf"
    
    md_path = os.path.join(temp_dir, md_filename)
    pdf_path = os.path.join(temp_dir, pdf_filename)
    
    # 3. Write content to MD file
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(request.content)
    except Exception as e:
        logger.error(f"Failed to write temp MD file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to write MD file: {str(e)}")
        
    # 4. Invoke tool
    try:
        # The tool expects md_path and pdf_path as arguments
        # Using ainvoke directly from the LangChain tool
        result = await tool.ainvoke({"md_path": md_path, "pdf_path": pdf_path})
        logger.info(f"MD to PDF tool result: {result}")
    except Exception as e:
        logger.error(f"PDF conversion failed: {e}")
        # Clean up MD file if failed
        if os.path.exists(md_path):
            os.remove(md_path)
        raise HTTPException(status_code=500, detail=f"PDF conversion failed: {str(e)}")
        
    # 5. Check if PDF exists
    if not os.path.exists(pdf_path):
         if os.path.exists(md_path):
            os.remove(md_path)
         logger.error(f"PDF file was not created at {pdf_path}")
         raise HTTPException(status_code=500, detail="PDF file was not created by the tool")
    
    # 6. Clean up task
    def cleanup_files():
        try:
            if os.path.exists(md_path):
                os.remove(md_path)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception as e:
            logger.error(f"Error cleaning up files: {e}")

    background_tasks.add_task(cleanup_files)
    
    # 7. Return file
    return FileResponse(
        path=pdf_path, 
        filename="conversation_export.pdf", 
        media_type="application/pdf"
    )

class MdToPptRequest(BaseModel):
    content: str

@router.post("/tools/md_to_ppt")
async def md_to_ppt(request: MdToPptRequest, background_tasks: BackgroundTasks):
    """
    Convert Markdown content to PPT using the 'mdtofiles' MCP server.
    """
    # 1. Check if tool exists
    tool = mcp_manager.get_tool("mdtofiles", "md_to_ppt_tool")
    if not tool:
        raise HTTPException(status_code=503, detail="MD to PPT tool not available. Ensure 'mdtofiles' MCP server is running.")

    # 2. Create temp directory
    temp_dir = os.path.join(os.getcwd(), "server", "data", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    task_id = str(uuid.uuid4())
    md_filename = f"{task_id}.md"
    ppt_filename = f"{task_id}.pptx"
    
    md_path = os.path.join(temp_dir, md_filename)
    ppt_path = os.path.join(temp_dir, ppt_filename)
    
    # 3. Write content to MD file
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(request.content)
    except Exception as e:
        logger.error(f"Failed to write temp MD file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to write MD file: {str(e)}")
        
    # 4. Invoke tool
    try:
        # The tool expects md_path and ppt_path as arguments
        result = await tool.ainvoke({"md_path": md_path, "ppt_path": ppt_path})
        logger.info(f"MD to PPT tool result: {result}")
    except Exception as e:
        logger.error(f"PPT conversion failed: {e}")
        if os.path.exists(md_path):
            os.remove(md_path)
        raise HTTPException(status_code=500, detail=f"PPT conversion failed: {str(e)}")
        
    # 5. Check if PPT exists
    if not os.path.exists(ppt_path):
         if os.path.exists(md_path):
            os.remove(md_path)
         logger.error(f"PPT file was not created at {ppt_path}")
         raise HTTPException(status_code=500, detail="PPT file was not created by the tool")
    
    # 6. Clean up task
    def cleanup_files():
        try:
            if os.path.exists(md_path):
                os.remove(md_path)
            if os.path.exists(ppt_path):
                os.remove(ppt_path)
        except Exception as e:
            logger.error(f"Error cleaning up files: {e}")

    background_tasks.add_task(cleanup_files)
    
    # 7. Return file
    return FileResponse(
        path=ppt_path, 
        filename="conversation_export.pptx", 
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )


class MdToDocxRequest(BaseModel):
    content: str


@router.post("/tools/md_to_docx")
async def md_to_docx(request: MdToDocxRequest, background_tasks: BackgroundTasks):
    """
    Convert Markdown content to DOCX using the 'mdtofiles' MCP server.
    """
    # 1. Check if tool exists
    tool = mcp_manager.get_tool("mdtofiles", "md_to_docx_tool")
    if not tool:
        raise HTTPException(status_code=503, detail="MD to DOCX tool not available. Ensure 'mdtofiles' MCP server is running.")

    # 2. Create temp directory
    temp_dir = os.path.join(os.getcwd(), "server", "data", "temp")
    os.makedirs(temp_dir, exist_ok=True)

    task_id = str(uuid.uuid4())
    md_filename = f"{task_id}.md"
    docx_filename = f"{task_id}.docx"

    md_path = os.path.join(temp_dir, md_filename)
    docx_path = os.path.join(temp_dir, docx_filename)

    # 3. Write content to MD file
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(request.content)
    except Exception as e:
        logger.error(f"Failed to write temp MD file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to write MD file: {str(e)}")

    # 4. Invoke tool
    try:
        result = await tool.ainvoke({"md_path": md_path, "docx_path": docx_path})
        logger.info(f"MD to DOCX tool result: {result}")
    except Exception as e:
        logger.error(f"DOCX conversion failed: {e}")
        if os.path.exists(md_path):
            os.remove(md_path)
        raise HTTPException(status_code=500, detail=f"DOCX conversion failed: {str(e)}")

    # 5. Check if DOCX exists
    if not os.path.exists(docx_path):
        if os.path.exists(md_path):
            os.remove(md_path)
        logger.error(f"DOCX file was not created at {docx_path}")
        raise HTTPException(status_code=500, detail="DOCX file was not created by the tool")

    # 6. Clean up task
    def cleanup_files():
        try:
            if os.path.exists(md_path):
                os.remove(md_path)
            if os.path.exists(docx_path):
                os.remove(docx_path)
        except Exception as e:
            logger.error(f"Error cleaning up files: {e}")

    background_tasks.add_task(cleanup_files)

    # 7. Return file
    return FileResponse(
        path=docx_path,
        filename="conversation_export.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
