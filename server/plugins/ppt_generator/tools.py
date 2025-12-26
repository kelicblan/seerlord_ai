import uuid
from pathlib import Path
from langchain_core.tools import tool
from server.kernel.mcp_manager import mcp_manager
from loguru import logger
from .schema import GeneratePPTInput

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
        base_dir = (Path.cwd() / "server" / "data" / "user_files" / safe_user_id).resolve()
        base_dir.mkdir(parents=True, exist_ok=True)
        
        task_id = str(uuid.uuid4())
        md_filename = f"ppt_{task_id}.md"
        ppt_filename = f"ppt_{task_id}.pptx"
        
        md_path = (base_dir / md_filename).resolve()
        ppt_path = (base_dir / ppt_filename).resolve()
        
        # 3. 写入 Markdown 文件
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        # 4. 调用 MCP 工具生成 PPT
        # MCP 工具期望的是文件路径
        await ppt_tool.ainvoke({"md_path": str(md_path), "ppt_path": str(ppt_path)})

        relative_path = f"{safe_user_id}/{ppt_filename}"
        return f"PPT 生成成功（可在内容广场下载）。path:{relative_path}"
        
    except Exception as e:
        logger.error(f"Generate PPT failed: {e}")
        return f"PPT 生成失败: {str(e)}"
