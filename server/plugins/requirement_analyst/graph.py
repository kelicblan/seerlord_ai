from typing import Dict, Any, List, Iterable, Tuple, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_text_splitters import RecursiveCharacterTextSplitter
import asyncio

from server.core.llm import get_llm
from .state import RequirementAnalystState
from .tools import parse_document_tool, generate_docx_tool
from server.core.database import SessionLocal
from server.models.artifact import AgentArtifact
from server.kernel.mcp_manager import mcp_manager
from server.kernel.skill_integration import skill_injector
import uuid
import yaml
import os
import re
import base64
from pathlib import Path

# Load Config
current_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(current_dir, "config.yaml"), "r", encoding="utf-8") as f:
    config_data = yaml.safe_load(f)
    SYSTEM_PROMPT = config_data.get("system_prompt", "")
    DOC1_PROMPT = config_data.get("doc1_prompt", "")
    DOC2_PROMPT = config_data.get("doc2_prompt", "")

# LLM
llm = get_llm()

from loguru import logger

_MERMAID_BLOCK_RE = re.compile(r"```mermaid\s*([\s\S]*?)```", re.IGNORECASE)
_MERMAID_FIRST_TOKEN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)")
_MERMAID_NON_ASCII_RE = re.compile(r"[^\x00-\x7F]")

_MERMAID_KNOWN_TYPES = {
    "graph",
    "flowchart",
    "sequencediagram",
    "classdiagram",
    "statediagram",
    "statediagram-v2",
    "erdiagram",
    "journey",
    "gantt",
    "pie",
    "mindmap",
    "timeline",
}


def _extract_tokens(response) -> int:
    try:
        if hasattr(response, "response_metadata"):
            usage = response.response_metadata.get("token_usage", {})
            return usage.get("total_tokens", 0)
    except Exception:
        pass
    return 0


def _iter_mermaid_blocks(markdown: str) -> Iterable[Tuple[Tuple[int, int], str]]:
    for m in _MERMAID_BLOCK_RE.finditer(markdown):
        yield (m.start(1), m.end(1)), m.group(1)


def _is_likely_gantt(code: str) -> bool:
    for line in code.splitlines():
        s = line.strip()
        if not s:
            continue
        return s.lower().startswith("gantt")
    return False


def _get_mermaid_type(code: str) -> Optional[str]:
    for raw in code.splitlines():
        s = raw.strip()
        if not s:
            continue
        m = _MERMAID_FIRST_TOKEN_RE.match(s)
        if not m:
            return None
        return m.group(1).lower()
    return None


def _looks_valid_gantt(code: str) -> bool:
    has_date_format = False
    has_task = False
    date_re = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")

    for raw in code.splitlines():
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("dateformat"):
            has_date_format = True
        if ":" in line and (date_re.search(line) or re.search(r"\b\d+d\b", line)):
            has_task = True

    return has_date_format and has_task


async def _fix_gantt_code(code: str, config: RunnableConfig) -> str:
    llm_fix = get_llm(temperature=0)
    prompt = (
        "你是 Mermaid Gantt 语法修复器。\n"
        "要求：\n"
        "1) 只输出修复后的 Mermaid Gantt 代码本体（不包含 ```）。\n"
        "2) 必须能被 Mermaid 正常解析渲染。\n"
        "3) 不要输出任何解释、标题或多余文本。\n"
    )
    resp = await llm_fix.ainvoke(
        [
            SystemMessage(content=prompt),
            HumanMessage(content=f"请修复以下 Mermaid Gantt 代码：\n\n{code.strip()}")
        ],
        config
    )
    fixed = (resp.content or "").strip()
    fixed = fixed.strip("`").strip()
    if not fixed:
        return code
    if "```" in fixed:
        fixed = fixed.replace("```mermaid", "").replace("```", "").strip()
    if not _is_likely_gantt(fixed):
        return code
    return fixed


async def _fix_mermaid_code(code: str, config: RunnableConfig) -> str:
    llm_fix = get_llm(temperature=0)
    prompt = (
        "你是 Mermaid 语法修复器。\n"
        "目标：把输入的 Mermaid 代码修复为“可被 Mermaid 正常解析渲染”的版本，并尽量保持原意。\n"
        "硬性规则：\n"
        "1) 只输出 Mermaid 代码本体（不包含 ```）。\n"
        "2) 节点/参与者的 ID 必须使用英文/数字/下划线（例如 A1、node_ok、Step_2）。\n"
        "3) 中文或带空格的文本只能放在标签里（例如 A[点击申请]、B(\"推送审批\")、C[\"xxx\"]）。\n"
        "4) 连接上的文字一律使用 Mermaid 合法写法（例如 flowchart/graph 用 --|文字|--> 或 -->|文字|）。\n"
        "5) 不要输出任何解释、标题或多余文本。\n"
    )
    resp = await llm_fix.ainvoke(
        [
            SystemMessage(content=prompt),
            HumanMessage(content=f"请修复以下 Mermaid 代码：\n\n{code.strip()}")
        ],
        config
    )

    fixed = (resp.content or "").strip()
    fixed = fixed.strip("`").strip()
    if not fixed:
        return code
    if "```" in fixed:
        fixed = fixed.replace("```mermaid", "").replace("```", "").strip()

    fixed_type = _get_mermaid_type(fixed)
    original_type = _get_mermaid_type(code)
    if original_type and fixed_type and fixed_type != original_type:
        return code

    return fixed


async def _validate_and_fix_mermaid(markdown: str, config: RunnableConfig) -> str:
    blocks = list(_iter_mermaid_blocks(markdown))
    if not blocks:
        return markdown

    parts: List[str] = []
    cursor = 0
    for (start, end), code in blocks:
        parts.append(markdown[cursor:start])
        fixed_code = code
        mermaid_type = _get_mermaid_type(code)
        if mermaid_type in _MERMAID_KNOWN_TYPES:
            should_fix = False
            if _is_likely_gantt(code) and not _looks_valid_gantt(code):
                should_fix = True
            if _MERMAID_NON_ASCII_RE.search(code or ""):
                should_fix = True
            if should_fix:
                if _is_likely_gantt(code):
                    fixed_code = await _fix_gantt_code(code, config)
                else:
                    fixed_code = await _fix_mermaid_code(code, config)
        parts.append(fixed_code)
        cursor = end
    parts.append(markdown[cursor:])
    return "".join(parts)


async def process_mermaid_images(content: str, user_id: str) -> str:
    """
    处理 Markdown 中的 Mermaid 代码块，使用 MCP 工具将其转换为 PNG 图片，
    并将代码块替换为图片链接。
    """
    blocks = list(_iter_mermaid_blocks(content))
    if not blocks:
        return content

    # 获取 mermaid 工具
    mermaid_tool = mcp_manager.get_tool("mermaid", "generate")
    if not mermaid_tool:
        logger.warning("Mermaid MCP tool 'generate' not found. Skipping image generation.")
        return content

    # 准备图片存储目录
    safe_user_id = "".join(ch for ch in (user_id or "unknown") if ch.isalnum() or ch in {"-", "_"})
    base_dir = (Path.cwd() / "server" / "data" / "user_files" / safe_user_id / "images").resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    parts: List[str] = []
    cursor = 0
    
    for (start, end), code in blocks:
        parts.append(content[cursor:start])
        
        try:
            # 生成唯一文件名
            image_filename = f"mermaid_{uuid.uuid4()}.png"
            image_path = base_dir / image_filename
            
            logger.info(f"Generating mermaid image: {image_filename}")
            
            # 调用 MCP 工具
            # 根据我们的分析，如果设置了 CONTENT_IMAGE_SUPPORTED=false，
            # 我们应该提供 folder/name 参数，它会返回路径。
            # 如果是默认值 (true)，它会返回 base64 内容。
            # 我们尝试先传递 folder/name，因为如果支持的话这是最高效的。
            
            tool_args = {
                "code": code,
                "folder": str(base_dir),
                "name": image_filename.replace(".png", "") # 工具可能会自动添加后缀
            }
            
            result = await mermaid_tool.ainvoke(tool_args)
            
            final_path = str(image_path)
            
            # 检查结果是否包含实际路径（工具可能返回 "PNG saved to: ..."）
            if isinstance(result, str):
                clean_result = result.strip()
                if clean_result.startswith("PNG saved to:"):
                    clean_result = clean_result.replace("PNG saved to:", "").strip()
                
                if (":" in clean_result or "/" in clean_result or "\\" in clean_result) and os.path.exists(clean_result):
                    final_path = clean_result
            
            # 验证文件是否存在
            if os.path.exists(final_path):
                # 使用绝对路径进行本地 docx 生成
                parts.append(f"![Mermaid Diagram]({final_path})\n")
            else:
                logger.warning(f"Mermaid generation finished but file not found at {final_path}")
                parts.append(f"```mermaid\n{code}\n```") # 回退
                
        except Exception as e:
            logger.error(f"Failed to generate mermaid image: {e}")
            parts.append(f"```mermaid\n{code}\n```") # 回退
            
        cursor = end
        
    parts.append(content[cursor:])
    return "".join(parts)


# Helper to find file path in messages
def extract_file_path(messages: List[BaseMessage | Dict[str, Any]]) -> str | None:
    # Look for file path in user message content
    for msg in reversed(messages):
        content: str | None = None
        if isinstance(msg, HumanMessage):
            content = msg.content
        elif isinstance(msg, dict):
            msg_type = str(msg.get("type") or msg.get("role") or "").lower()
            if msg_type in {"human", "user"}:
                raw_content = msg.get("content")
                if isinstance(raw_content, str):
                    content = raw_content
                elif isinstance(raw_content, list):
                    content = "\n".join(str(x) for x in raw_content)
                elif raw_content is not None:
                    content = str(raw_content)

        if content is not None:
            logger.info(f"Checking message for path (raw repr): {repr(content)[:500]}")
            
            # 0. Normalize content: replace escaped backslashes which might come from JSON inputs
            content = content.replace('\\\\', '\\')
            
            # Normalize hidden/weird characters
            content = content.replace('\u200b', '') # Zero-width space
            content = content.replace('\u2212', '-') # Minus sign
            content = content.replace('\u2013', '-').replace('\u2014', '-') # Dashes

            # 1. Try to match explicit [附件: path] format (with or without brackets)
            attachment_match = re.search(r'\[?附件:\s*(.*?)(\]|[\r\n]|$)', content)
            if attachment_match:
                path = attachment_match.group(1).strip()
                if path.endswith(']'):
                    path = path[:-1].strip()
                
                # Check if it looks like a valid path (at least has a drive letter or slash)
                if path and (':' in path or '/' in path or '\\' in path):
                    # Clean up quotes
                    path = path.strip('"').strip("'")
                    logger.info(f"Found path via attachment prefix: {path}")
                    return path
                else:
                    logger.warning(f"Path candidate found but invalid: {repr(path)}")
            
            # 1.5 Check for Markdown link [text](path) - Common in chat UIs
            md_link_match = re.search(r'\[.*?\]\((.*?)\)', content)
            if md_link_match:
                path = md_link_match.group(1).strip()
                # Remove file:// prefix if present
                if path.startswith('file:///'):
                    path = path[8:]
                elif path.startswith('file://'):
                    path = path[7:]
                
                if path and (':' in path or '/' in path or '\\' in path):
                    path = path.strip('"').strip("'")
                    logger.info(f"Found path via Markdown link: {path}")
                    return path

            # 2. Aggressive Regex for absolute file paths (Windows/Linux)
            # Matches: Drive letter followed by colon and backslash/slash (C:\... or C:/...) OR just slash (/...)
            # It captures until it hits a newline, quote, or end of string.
            # We specifically look for common document extensions to reduce false positives, 
            # BUT we allow spaces and other chars.
            
            # Pattern explanation:
            # ([a-zA-Z]:[\\/][^"\n\r<>|?*]+?\.(docx|pdf|md|txt))  -> Windows absolute path (supports \ and /)
            # (/[^"\n\r<>|?*]+?\.(docx|pdf|md|txt))            -> Linux/Mac absolute path
            
            path_pattern = r'([a-zA-Z]:[\\/][^"\n\r<>|?*]+?\.(docx|pdf|md|txt))|(/[^"\n\r<>|?*]+?\.(docx|pdf|md|txt))'
            match = re.search(path_pattern, content, re.IGNORECASE)
            if match:
                path = match.group(0).strip()
                logger.info(f"Found path via regex: {path}")
                return path

    logger.warning("No file path found in messages.")
    return None

async def parse_input(state: RequirementAnalystState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node 1: Identify file and parse it.
    """
    messages = state["messages"]
    file_path = state.get("input_file_path")
    logger.info(f"Initial input_file_path: {file_path}")
    
    if not file_path:
        file_path = extract_file_path(messages)
    
    # CRITICAL FIX: If no file path found, return a specific error state that check_parse_success can handle
    # AND ensure the message is returned to the user via LLM stream.
    if not file_path:
        msg = "未检测到有效的文件路径。请提供 .docx 或 .pdf 文件的绝对路径（例如：E:\\data\\req.docx）。"
        # Use LLM to stream the error message so it appears in frontend
        await llm.ainvoke([SystemMessage(content="You are a helpful assistant."), HumanMessage(content=f"Tell the user exactly this: {msg}")], config)
        return {
            "parsed_content": f"Error: {msg}",
            "messages": [AIMessage(content=msg)]
        }

    # Call tool to parse
    # Ensure path is clean
    file_path = file_path.strip().strip('"').strip("'")
    
    logger.info(f"Invoking parse_document_tool with path: {file_path}")
    content = await parse_document_tool.ainvoke(file_path)
    
    if content.startswith("Error"):
        # Return error as parsed_content so check_parse_success can see it
        # Also return message to user
        err_msg = f"解析文件失败：{content}"
        await llm.ainvoke([SystemMessage(content="You are a helpful assistant."), HumanMessage(content=f"Tell the user exactly this: {err_msg}")], config)
        return {
            "parsed_content": content,
            "messages": [AIMessage(content=err_msg)]
        }
        
    # Get clean filename for display (handles both / and \)
    file_name_display = file_path.replace('\\', '/').split('/')[-1]
    logger.info(f"Invoking 已识别文件: {file_name_display}")
    
    # Stream progress message
    progress_msg = f"已识别文件：{file_name_display}\n正在解析文档并分析需求..."
    await llm.ainvoke([SystemMessage(content="You are a helpful assistant."), HumanMessage(content=f"Tell the user exactly this: {progress_msg}")], config)
    
    return {
        "input_file_path": file_path, 
        "parsed_content": content,
        "messages": [AIMessage(content=progress_msg)]
    }

MAX_CONTEXT_CHARS = 30000

async def compress_content(text: str, config: RunnableConfig) -> str:
    """
    Compress large requirement documents by summarizing chunks.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=12000,
        chunk_overlap=500
    )
    chunks = splitter.split_text(text)
    
    if len(chunks) <= 1:
        return text
        
    logger.info(f"Compressing content: {len(text)} chars -> {len(chunks)} chunks")
    
    summarized_chunks = []
    
    # Process chunks in batches to avoid rate limits
    batch_size = 3
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        tasks = []
        for chunk in batch:
            prompt = (
                "You are an expert Requirement Analyst. "
                "Please summarize the following section of a requirement document. "
                "CRITICAL: Retain all functional requirements, business rules, user roles, and technical constraints. "
                "Remove only filler words and redundant introductions. "
                "Output in Markdown format.\n\n"
                f"{chunk}"
            )
            tasks.append(llm.ainvoke([HumanMessage(content=prompt)], config))
        
        results = await asyncio.gather(*tasks)
        for res in results:
            summarized_chunks.append(res.content)
            
    compressed_text = "\n\n".join(summarized_chunks)
    logger.info(f"Compression complete: {len(text)} -> {len(compressed_text)} chars")
    return compressed_text

async def optimize_context(state: RequirementAnalystState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node 1.5: Optimize context if content is too large.
    """
    content = state.get("parsed_content", "")
    if len(content) > MAX_CONTEXT_CHARS:
        msg = f"文档内容较长 ({len(content)} 字符)，正在进行智能压缩与提炼，请稍候..."
        await llm.ainvoke([SystemMessage(content="You are a helpful assistant."), HumanMessage(content=f"Tell the user exactly this: {msg}")], config)
        
        compressed = await compress_content(content, config)
        return {
            "parsed_content": compressed,
            "messages": [AIMessage(content="文档压缩完成，开始生成文档...")]
        }
    return {}

async def generate_doc1(state: RequirementAnalystState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node 2: Generate Document 1 (Project Specs)
    """
    parsed_content = state.get("parsed_content")
    if not parsed_content:
        return {} # Should not happen if parse_input succeeds

    skills = state.get("skills_context", "")
    sys_prompt = SYSTEM_PROMPT
    if skills:
        sys_prompt += f"\n\n[Expert Guidelines]:\n{skills}"

    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content=f"{DOC1_PROMPT}\n\n以下是需求文档原始内容：\n\n{parsed_content}")
    ]
    
    response = await llm.ainvoke(messages, config)
    tokens = _extract_tokens(response)
    current_tokens = state.get("total_tokens", 0)
    
    doc1_content = await _validate_and_fix_mermaid(response.content or "", config)
    return {
        "doc1_content": doc1_content,
        "messages": [AIMessage(content="《项目需求规格说明书与实施方案》初稿生成完毕，正在生成第二份文档...")],
        "total_tokens": current_tokens + tokens
    }

async def generate_doc2(state: RequirementAnalystState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node 3: Generate Document 2 (Dev Guide)
    """
    parsed_content = state.get("parsed_content")
    if not parsed_content:
        return {}

    skills = state.get("skills_context", "")
    sys_prompt = SYSTEM_PROMPT
    if skills:
        sys_prompt += f"\n\n[Expert Guidelines]:\n{skills}"

    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content=f"{DOC2_PROMPT}\n\n以下是需求文档原始内容：\n\n{parsed_content}")
    ]
    
    response = await llm.ainvoke(messages, config)
    tokens = _extract_tokens(response)
    current_tokens = state.get("total_tokens", 0)
    
    doc2_content = await _validate_and_fix_mermaid(response.content or "", config)
    return {
        "doc2_content": doc2_content,
        "messages": [AIMessage(content="《系统开发综合指导手册》初稿生成完毕，正在进行格式转换和打包...")],
        "total_tokens": current_tokens + tokens
    }

async def convert_and_finalize(state: RequirementAnalystState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node 4: Convert generated MD to DOCX and output links.
    """
    doc1 = state.get("doc1_content")
    doc2 = state.get("doc2_content")
    
    if not doc1 or not doc2:
         return {"messages": [AIMessage(content="生成文档内容失败，请重试。")]}

    configurable = config.get("configurable", {})
    tenant_id = configurable.get("tenant_id")
    user_id = configurable.get("user_id") or tenant_id

    # Process Mermaid images before generating DOCX
    logger.info("Processing Mermaid images for DOCX...")
    try:
        doc1 = await process_mermaid_images(doc1, str(user_id))
        doc2 = await process_mermaid_images(doc2, str(user_id))
    except Exception as e:
        logger.error(f"Error processing mermaid images: {e}")
        # Continue even if image processing fails

    # Generate DOCX
    res1 = await generate_docx_tool.ainvoke({"content": doc1, "filename_prefix": "Project_Spec", "user_id": user_id})
    res2 = await generate_docx_tool.ainvoke({"content": doc2, "filename_prefix": "Dev_Guide", "user_id": user_id})
    
    def parse_doc_result(res: Any) -> tuple[str | None, str | None, str]:
        if isinstance(res, str):
            raw = res
        else:
            try:
                raw = str(res)
            except Exception:
                raw = repr(res)

        path: str | None = None
        url: str | None = None

        if "path:" in raw:
            after_path = raw.split("path:", 1)[1]
            if "|url:" in after_path:
                path = after_path.split("|url:", 1)[0].strip()
            else:
                path = after_path.strip()

        if "url:" in raw:
            url = raw.split("url:", 1)[1].strip()
        
        # Handle "Download Link:" format (S3)
        if "Download Link:" in raw:
            url = raw.split("Download Link:", 1)[1].strip()
        
        # Fallback: Check if raw is just a URL
        if not url and (raw.strip().startswith("http://") or raw.strip().startswith("https://")):
             url = raw.strip()

        return path, url, raw

    path1, url1, raw1 = parse_doc_result(res1)
    path2, url2, raw2 = parse_doc_result(res2)
    
    # Save Artifacts to DB
    try:
        if tenant_id:
            current_tokens = state.get("total_tokens", 0)
            async with SessionLocal() as db:
                if path1 or url1:
                    val1 = url1 if url1 else path1
                    db.add(AgentArtifact(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant_id,
                        user_id=user_id,
                        agent_id="requirement_analyst",
                        type="file",
                        value=val1,
                        title="项目需求规格说明书与实施方案",
                        description="自动生成的需求规格说明书",
                        total_tokens=current_tokens
                    ))
                if path2 or url2:
                    val2 = url2 if url2 else path2
                    db.add(AgentArtifact(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant_id,
                        user_id=user_id,
                        agent_id="requirement_analyst",
                        type="file",
                        value=val2,
                        title="系统开发综合指导手册",
                        description="自动生成的开发指导手册",
                        total_tokens=current_tokens
                    ))
                await db.commit()
    except Exception as e:
        logger.error(f"Failed to save artifacts: {e}")

    final_msg = "需求分析完成！已为您生成以下两份文档：\n\n"
    if path1 or url1:
        link1 = url1 if url1 else path1
        final_msg += f"1. 项目需求规格说明书与实施方案：已生成\n   [点击下载]({link1})\n"
    else:
        final_msg += f"1. 项目需求规格说明书与实施方案：生成失败 ({raw1})\n"

    if path2 or url2:
        link2 = url2 if url2 else path2
        final_msg += f"2. 系统开发综合指导手册：已生成\n   [点击下载]({link2})\n"
    else:
        final_msg += f"2. 系统开发综合指导手册：生成失败 ({raw2})\n"

    response = await llm.ainvoke(
        [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=f"Tell the user exactly this:\n\n{final_msg}")
        ],
        config
    )
    
    tokens = _extract_tokens(response)
    current_tokens = state.get("total_tokens", 0)

    return {
        "doc1_path": path1,
        "doc2_path": path2,
        "messages": [AIMessage(content=final_msg)],
        "total_tokens": current_tokens + tokens
    }

# Build Graph
workflow = StateGraph(RequirementAnalystState)

workflow.add_node("load_skills", skill_injector.load_skills_context)
workflow.add_node("parse_input", parse_input)
workflow.add_node("optimize_context", optimize_context)
workflow.add_node("generate_doc1", generate_doc1)
workflow.add_node("generate_doc2", generate_doc2)
workflow.add_node("convert_and_finalize", convert_and_finalize)

workflow.set_entry_point("load_skills")
workflow.add_edge("load_skills", "parse_input")

# Edges
def check_parse_success(state: RequirementAnalystState):
    if state.get("parsed_content") and not state["parsed_content"].startswith("Error"):
        return "optimize_context"
    return END

workflow.add_conditional_edges("parse_input", check_parse_success, {"optimize_context": "optimize_context", END: END})
workflow.add_edge("optimize_context", "generate_doc1")
workflow.add_edge("generate_doc1", "generate_doc2")
workflow.add_edge("generate_doc2", "convert_and_finalize")
workflow.add_edge("convert_and_finalize", END)

app = workflow.compile()
