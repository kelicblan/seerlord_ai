import os
import uuid
import asyncio
from pathlib import Path
from langchain_core.tools import tool
from server.kernel.mcp_manager import mcp_manager
from loguru import logger
from .docx_utils import create_docx_from_md

@tool
async def parse_document_tool(file_path: str) -> str:
    """
    Parses a DOCX or PDF file and returns its content as Markdown.
    """
    try:
        # Clean up path (remove quotes, extra whitespace)
        file_path = file_path.strip().strip('"').strip("'")
        
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"
        
        logger.info(f"Parsing document: {file_path}")
        
        # Run MarkItDown in a separate thread to avoid blocking the event loop
        def _parse():
            from markitdown import MarkItDown
            md = MarkItDown()
            # Check if file is readable
            return md.convert(file_path)

        result = await asyncio.to_thread(_parse)
        logger.info(f"Document parsed successfully, length: {len(result.text_content)}")
        return result.text_content
    except Exception as e:
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext == ".docx":
            try:
                from docx import Document
                doc = Document(file_path)
                text = "\n".join(p.text for p in doc.paragraphs if p.text)
                logger.info(f"Document parsed via python-docx, length: {len(text)}")
                return text
            except Exception as fallback_e:
                logger.error(f"python-docx fallback failed for {file_path}: {fallback_e}")

        logger.error(f"Failed to parse document {file_path}: {e}")
        return f"Error parsing document: {str(e)}"

from server.core.storage import s3_client
import os

@tool
async def generate_docx_tool(content: str, filename_prefix: str, user_id: str | None = None) -> str:
    """
    Generates a DOCX file from Markdown content locally, supporting images.
    Returns the file path.
    """
    try:
        safe_user_id = "".join(ch for ch in (user_id or "unknown") if ch.isalnum() or ch in {"-", "_"})
        
        # Use temp directory for initial generation
        temp_dir = (Path.cwd() / "server" / "data" / "temp").resolve()
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        task_id = str(uuid.uuid4())
        md_filename = f"{filename_prefix}_{task_id}.md"
        docx_filename = f"{filename_prefix}_{task_id}.docx"
        
        md_path = (temp_dir / md_filename).resolve()
        docx_path = (temp_dir / docx_filename).resolve()
        
        # Write temp MD (optional, but good for debug)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        # Generate DOCX locally using our enhanced utility
        logger.info(f"Generating DOCX locally: {docx_path}")
        
        # Run in thread pool to avoid blocking async loop
        def _generate():
            return create_docx_from_md(content, str(docx_path))
            
        success = await asyncio.to_thread(_generate)
        
        if not success:
             return "Error: Failed to generate DOCX file."

        # S3 Upload
        if s3_client.enabled:
            object_name = f"docs/{safe_user_id}/{docx_filename}"
            s3_url = s3_client.upload_file(docx_path, object_name)
            if s3_url:
                try:
                    os.remove(docx_path)
                    os.remove(md_path)
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup temp files: {cleanup_err}")
                return f"Download Link: {s3_url}"

        # Fallback to local user_files
        user_dir = (Path.cwd() / "server" / "data" / "user_files" / safe_user_id).resolve()
        user_dir.mkdir(parents=True, exist_ok=True)
        final_docx_path = user_dir / docx_filename
        final_md_path = user_dir / md_filename
        
        import shutil
        shutil.move(str(docx_path), str(final_docx_path))
        if md_path.exists():
            shutil.move(str(md_path), str(final_md_path))
            
        relative_path = f"{safe_user_id}/{docx_filename}"
        return f"path:{relative_path}"

    except Exception as e:
        logger.error(f"Failed to generate DOCX: {e}")
        return f"Error generating DOCX: {str(e)}"
