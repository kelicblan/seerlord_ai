from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from server.core.llm import get_llm
from .state import UIDesignerState
from server.core.database import SessionLocal
from server.models.artifact import AgentArtifact
from server.core.storage import S3Client
from server.kernel.skill_integration import skill_injector

import os
import uuid
import json
import re
import base64
import mimetypes
from pathlib import Path
from loguru import logger

# --- Prompts ---

PROMPT_STEP_1_TEMPLATE = """Analyze the User Interface (UI) design in this screenshot.
Context from user: "{user_description}"
Use this context to narrow down the page type, specific style, and functional requirements.

Thoroughly describe the layout, hierarchy, and components in as much detail as you can to hand over from a UI designer to a developer. The brief should be both for light and dark mode and contain responsive breakpoints matching Tailwind CSS' defaults. Output characteristics as structured JSONC.
For colors, extract a rough palette and only detail accents and complex media. The goal is to use only 2 palettes: primary and secondary similar to Tailwind colors. Alongside these 2, you can define any number of grays and accept colors for more complex UI (gradients, shadows, illustrations, etc.)
End with a prompt explaining how to implement the UI for a developer, but don't mention any tech specs; only a brief of the UI to be implemented and the token rules + usage. Output the prompt as markdown code."""

PROMPT_STEP_2_TEMPLATE = """# Role
你是尤雨溪（Evan You），世界顶级的前端工程师，精通 **Vue 3** 和 **移动端/响应式设计** 架构等等。

# Task
请根据下方的 **[UI 设计规范]** 和 **[实现简报]**，编写一个高质量的 Vue 3 单文件组件 (`ChatInterface.vue`)。

# Technical Stack
1.  **Framework:** Vue 3 (Composition API + `<script setup>` + TypeScript).
2.  **Styling:** Tailwind CSS.
3.  **Icons:** 使用 `lucide-vue-next` 图标库（如果无法引入，请使用 SVG 代码占位）。

# Critical Requirements (Web & App Compatibility)
这个界面需要同时兼容 **Web 浏览器** 和 **移动 App (Webview/H5)**，请严格遵守以下布局逻辑：

1.  **视口布局 (Viewport Layout):**
    -   使用 `h-[100dvh]` (Dynamic Viewport Height) 确保在移动端浏览器地址栏伸缩时高度正确。
    -   **禁止全局滚动**：`body` 或最外层容器应设为 `overflow-hidden`。
    -   **Flex 结构**：采用 `Header(Fixed)` + `MessageList(Flex-1, Scrollable)` + `InputArea(Fixed)` 的经典三段式布局。

2.  **移动端原生体验 (App Feel):**
    -   **安全区域**: 必须在 Header (顶部) 和 InputArea (底部) 增加 `pt-safe` 和 `pb-safe` (或者 Tailwind 的 `pt-[env(safe-area-inset-top)]` / `pb-[env(safe-area-inset-bottom)]`)，以适配 iPhone 刘海屏和底部黑条。
    -   **触控优化**: 按钮点击区域要足够大 (min 44px)，输入框去除默认轮廓。

3.  **桌面端适配 (Desktop Adaptation):**
    -   在 `md` (平板/桌面) 断点以上，将主容器限制宽度 (`max-w-md` 或 `max-w-lg`) 并**水平居中**，使其在电脑屏幕上看起来像是一个悬浮的聊天窗口，两侧留白或显示背景色。

4.  **Mock Data:**
    -   请在代码中内置一份包含 3-5 条消息的模拟数据（包含文本、Emoji、时间戳），确保组件渲染出来就是有内容的。

---

**文档 1：UI 设计规范 (JSONC)**
{jsonc_content}

---

**文档 2：实现简报 (Markdown)**
{md_content}

---

# Output Format
请直接输出 **Vue 3 代码**，不要废话。确保代码包含了 Template, Script, 和 Style (Tailwind classes)。"""

# --- Tools / Structured Output ---

class DesignSpecs(BaseModel):
    """Output for the UI analysis step."""
    ui_design_spec_jsonc: str = Field(description="The UI design specification in JSONC format.")
    implementation_prompt_md: str = Field(description="The implementation prompt in Markdown format.")

# --- Nodes ---

async def analyze_ui_node(state: UIDesignerState, config: RunnableConfig) -> Dict[str, Any]:
    """Step 1: Analyze the image and generate specs."""
    logger.info("Starting UI Analysis...")
    messages = state["messages"]
    
    # Extract user description from the last message if available
    user_description = "No specific description provided."
    if messages and isinstance(messages[-1], HumanMessage):
        content = messages[-1].content
        if isinstance(content, str):
            # If it's just a string, it might be the description (if image is attached differently) 
            # or it might contain [附件: path] which we handled before.
            # We want to remove the [附件: ...] part to get the pure description.
            clean_text = re.sub(r'\[附件:.*?\]', '', content).strip()
            if clean_text:
                user_description = clean_text
        elif isinstance(content, list):
            # If it's a list (multimodal), find the text part
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "").strip()
                    if text:
                        user_description = text
                    break

    # Format the prompt with user description
    formatted_prompt = PROMPT_STEP_1_TEMPLATE.format(user_description=user_description)
    
    # Prepend System Prompt (with skills)
    skills = state.get("skills_context", "")
    sys_content = formatted_prompt
    if skills:
        sys_content = f"[Expert Design Guidelines]:\n{skills}\n\n" + sys_content
    
    # We construct a new history for this call.
    prompt_messages = [SystemMessage(content=sys_content)] + messages
    
    # Get LLM
    llm = get_llm(use_full_modal=True)
    
    try:
        # Try structured output first
        structured_llm = llm.with_structured_output(DesignSpecs)
        result: DesignSpecs = await structured_llm.ainvoke(prompt_messages)
        
        # Check if result is empty or invalid
        if not result.ui_design_spec_jsonc or len(result.ui_design_spec_jsonc) < 10:
             raise ValueError("Structured output returned empty JSONC")
        
        return {
            "ui_design_spec": result.ui_design_spec_jsonc,
            "implementation_prompt": result.implementation_prompt_md,
            "user_description": user_description
        }
    except Exception as e:
        logger.warning(f"Structured output failed in analyze_ui_node: {e}. Falling back to raw text parsing.")
        
        # Fallback: Invoke LLM directly and parse manually
        try:
            response = await llm.ainvoke(prompt_messages)
            content = response.content
            
            # Simple heuristic extraction
            jsonc_part = "// JSONC parsing failed"
            md_part = "Markdown parsing failed"
            
            # Extract JSONC (look for first { and last })
            # This is a naive extraction, assuming the largest brace block is the JSON
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                jsonc_candidate = content[start_idx:end_idx+1]
                # Verify if it looks like json
                jsonc_part = jsonc_candidate
            
            # Extract Markdown Prompt (usually after the JSON, or labeled)
            # We look for the text after the JSON part
            if end_idx != -1:
                remaining_text = content[end_idx+1:].strip()
                # Remove common markdown code block markers if present
                if "```markdown" in remaining_text:
                     md_part = remaining_text.split("```markdown")[1].split("```")[0].strip()
                elif "```" in remaining_text:
                     # Check if it's just a closing block or an opening one
                     parts = remaining_text.split("```")
                     # If there are 3 parts (text ``` code ``` text), take the middle
                     if len(parts) >= 3:
                         md_part = parts[1].strip()
                     elif len(parts) == 2:
                         # text ``` code or code ``` text
                         md_part = parts[1].strip() if not parts[0].strip() else parts[0].strip()
                     else:
                         md_part = remaining_text.replace("```", "").strip()
                else:
                     md_part = remaining_text
            
            # If MD extraction failed but JSON succeeded, maybe the whole remaining text is the prompt
            if (md_part == "Markdown parsing failed" or not md_part) and end_idx != -1:
                 md_part = content[end_idx+1:].strip()

            return {
                "ui_design_spec": jsonc_part,
                "implementation_prompt": md_part,
                "user_description": user_description
            }
            
        except Exception as e2:
            logger.error(f"Fallback parsing also failed: {e2}")
            return {
                "ui_design_spec": f"// Error parsing JSONC: {str(e)}",
                "implementation_prompt": f"Error parsing Markdown: {str(e)}",
                "user_description": user_description
            }

async def generate_code_node(state: UIDesignerState, config: RunnableConfig) -> Dict[str, Any]:
    """Step 2: Generate Vue code from specs."""
    logger.info("Starting Code Generation...")
    
    jsonc = state.get("ui_design_spec", "")
    md = state.get("implementation_prompt", "")
    
    # Construct the Step 2 prompt
    final_prompt = PROMPT_STEP_2_TEMPLATE.format(jsonc_content=jsonc, md_content=md)
    
    skills = state.get("skills_context", "")
    if skills:
        final_prompt = f"[Expert Implementation Guidelines]:\n{skills}\n\n" + final_prompt

    llm = get_llm(use_full_modal=True)
    response = await llm.ainvoke([HumanMessage(content=final_prompt)])
    
    code = response.content
    
    # Extract code block if present
    if "```vue" in code:
        code = code.split("```vue")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()
        
    # Save to file and artifact
    configurable = config.get("configurable", {})
    tenant_id = configurable.get("tenant_id")
    user_id = configurable.get("user_id") or tenant_id or "unknown"
    
    # Ensure safe user_id
    safe_user_id = "".join(ch for ch in str(user_id) if ch.isalnum() or ch in {"-", "_"})
    
    filename = f"ChatInterface_{uuid.uuid4().hex[:8]}.vue"
    
    # Use S3Client for storage
    s3_client = S3Client()
    file_url = None
    artifact_value = None
    
    if s3_client.enabled:
        # Create temp directory
        temp_dir = (Path.cwd() / "server" / "data" / "temp").resolve()
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file_path = temp_dir / filename
        
        try:
            # Write to temp file
            with open(temp_file_path, "w", encoding="utf-8") as f:
                f.write(code)
            
            # Upload to S3
            object_name = f"ui_components/{safe_user_id}/{filename}"
            file_url = s3_client.upload_file(temp_file_path, object_name)
            
            if file_url:
                logger.info(f"Generated UI code uploaded to S3: {file_url}")
                artifact_value = file_url
                
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
        finally:
            # Cleanup temp file
            if temp_file_path.exists():
                try:
                    os.remove(temp_file_path)
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup temp file {temp_file_path}: {cleanup_err}")

    # Fallback to local storage if S3 is disabled or failed
    if not file_url:
        base_dir = (Path.cwd() / "server" / "data" / "user_files" / safe_user_id).resolve()
        base_dir.mkdir(parents=True, exist_ok=True)
        file_path = base_dir / filename
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        logger.info(f"Generated UI code saved to local: {file_path}")
        # For local files, we might store the relative path or a specific format
        # Previously it was: value=f"{safe_user_id}/{filename}"
        artifact_value = f"{safe_user_id}/{filename}"
        
    # Save Artifact
    if tenant_id and artifact_value:
        try:
            async with SessionLocal() as db:
                db.add(AgentArtifact(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    user_id=user_id,
                    agent_id="ui_designer",
                    type="file",
                    value=artifact_value,
                    title="Vue 3 Component",
                    description="Generated from UI Screenshot"
                ))
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to save artifact: {e}")

    return {
        "final_code": code,
        "messages": [AIMessage(content=f"UI Generation Complete! Saved as {filename}. URL: {artifact_value}")]
    }

# --- Graph ---

workflow = StateGraph(UIDesignerState)

workflow.add_node("load_skills", skill_injector.load_skills_context)
workflow.add_node("analyze_ui", analyze_ui_node)
workflow.add_node("generate_code", generate_code_node)

workflow.set_entry_point("load_skills")
workflow.add_edge("load_skills", "analyze_ui")
workflow.add_edge("analyze_ui", "generate_code")
workflow.add_edge("generate_code", END)

app = workflow.compile()
