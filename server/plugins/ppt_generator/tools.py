import uuid
from pathlib import Path
from langchain_core.tools import tool
from server.kernel.mcp_manager import mcp_manager
from loguru import logger
from .schema import GeneratePPTInput
from server.core.storage import s3_client
import os

@tool("generate_ppt", args_schema=GeneratePPTInput)
async def generate_ppt(md_content: str, user_id: str | None = None) -> str:
    """
    根据Markdown内容生成PPT文件。
    返回生成的文件下载链接或路径信息。
    """
    try:
        # 1. 获取 MCP 工具
        ppt_tool = mcp_manager.get_tool("mdtofiles", "md_to_ppt_tool")
        if not ppt_tool:
            return "Error: 'mdtofiles' MCP server or 'md_to_ppt_tool' not available."

        safe_user_id = "".join(ch for ch in (user_id or "unknown") if ch.isalnum() or ch in {"-", "_"})
        
        # Use temp directory for initial generation
        temp_dir = (Path.cwd() / "server" / "data" / "temp").resolve()
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        task_id = str(uuid.uuid4())
        md_filename = f"ppt_{task_id}.md"
        ppt_filename = f"ppt_{task_id}.pptx"
        
        md_path = (temp_dir / md_filename).resolve()
        ppt_path = (temp_dir / ppt_filename).resolve()
        
        # 3. 写入 Markdown 文件
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        # 4. 调用 MCP 工具生成 PPT
        # MCP 工具期望的是文件路径
        await ppt_tool.ainvoke({"md_path": str(md_path), "ppt_path": str(ppt_path)})

        # 5. 上传到 S3
        if s3_client.enabled:
            object_name = f"ppt/{safe_user_id}/{ppt_filename}"
            s3_url = s3_client.upload_file(ppt_path, object_name)
            if s3_url:
                # 成功上传，删除本地文件
                try:
                    os.remove(ppt_path)
                    os.remove(md_path)
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup temp files: {cleanup_err}")
                return f"PPT 生成成功。下载链接: {s3_url}"
        
        # Fallback to local user_files
        user_dir = (Path.cwd() / "server" / "data" / "user_files" / safe_user_id).resolve()
        user_dir.mkdir(parents=True, exist_ok=True)
        final_ppt_path = user_dir / ppt_filename
        final_md_path = user_dir / md_filename
        
        import shutil
        shutil.move(str(ppt_path), str(final_ppt_path))
        if md_path.exists():
            shutil.move(str(md_path), str(final_md_path))
            
        relative_path = f"{safe_user_id}/{ppt_filename}"
        return f"PPT 生成成功（可在内容广场下载）。path:{relative_path}"
        
    except Exception as e:
        logger.error(f"Generate PPT failed: {e}")
        return f"PPT 生成失败: {str(e)}"
