from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from server.core.llm import get_llm
from .state import PPTGeneratorState
from .tools import generate_ppt
from server.kernel.skill_integration import skill_injector
import yaml
import os
import uuid
from server.core.database import SessionLocal
from server.models.artifact import AgentArtifact
from loguru import logger

# 加载 Prompt
current_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(current_dir, "config.yaml"), "r", encoding="utf-8") as f:
    config_data = yaml.safe_load(f)
    SYSTEM_PROMPT = config_data.get("prompt", "")

# 初始化 LLM 和 Tools
llm = get_llm()
tools = [generate_ppt]
llm_with_tools = llm.bind_tools(tools)

async def analyze_and_generate(state: PPTGeneratorState, config: RunnableConfig) -> Dict[str, Any]:
    """
    分析用户输入，生成 Markdown 并调用工具生成 PPT
    """
    messages = state["messages"]
    
    # 获取技能上下文
    skills = state.get("skills_context", "")
    full_system_prompt = SYSTEM_PROMPT
    if skills:
        full_system_prompt += f"\n\n[Expert Guidelines]:\n{skills}"

    # 确保系统提示词在最前
    if not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=full_system_prompt)] + messages
    else:
        # 如果已经有 SystemMessage (比如从 load_skills 来的?)
        # SkillInjector 已经在 messages 列表里放了一个 SystemMessage。
        # 这里我们是想合并，还是追加？
        # SkillInjector 的消息是 "Dynamic Skills Active..."
        # 这里的 SYSTEM_PROMPT 是 "你是 PPT 生成助手..."
        # 最好是保留两个 SystemMessage，LangChain 会处理。
        # 但这里代码强制替换了第一个？
        # "if not isinstance(messages[0], SystemMessage)" -> 如果第一个不是 SystemMessage，就加一个。
        # 如果第一个已经是 SkillInjector 的 SystemMessage，这里就不会加 SYSTEM_PROMPT 了！
        # 这是一个 Bug 隐患。
        # 修正逻辑：不管有没有，我们都要把我们的业务 Prompt 加上。
        # 我们可以插入到开头，或者追加。
        pass
        
    # 修正逻辑：
    # SkillInjector 会在 messages 列表末尾追加 SystemMessage (实际上是追加到 state['messages'])。
    # 当我们这里取 state['messages'] 时，它包含用户消息和技能消息。
    # 我们应该把业务 Prompt 放在最前面。
    
    prompts = [SystemMessage(content=SYSTEM_PROMPT)]
    if skills:
        prompts.append(SystemMessage(content=f"[Expert Guidelines]:\n{skills}"))
        
    # Filter out existing SystemMessages if we want to avoid duplication?
    # No, let's just prepend.
    final_messages = prompts + messages
    
    response = await llm_with_tools.ainvoke(final_messages, config)
    
    return {"messages": [response]}

async def execute_tools(state: PPTGeneratorState, config: RunnableConfig) -> Dict[str, Any]:
    """
    执行工具调用
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    if not last_message.tool_calls:
        return {"messages": []}
        
    results = []
    for tool_call in last_message.tool_calls:
        if tool_call["name"] == "generate_ppt":
            configurable = config.get("configurable", {})
            tenant_id = configurable.get("tenant_id")
            user_id = configurable.get("user_id") or tenant_id

            tool_args = dict(tool_call.get("args") or {})
            tool_args["user_id"] = user_id
            tool_output = await generate_ppt.ainvoke(tool_args)

            raw = str(tool_output)
            relative_path = None
            if "path:" in raw:
                relative_path = raw.split("path:", 1)[1].strip()

            if tenant_id and relative_path:
                try:
                    async with SessionLocal() as db:
                        db.add(
                            AgentArtifact(
                                id=str(uuid.uuid4()),
                                tenant_id=tenant_id,
                                user_id=user_id,
                                agent_id="ppt_generator",
                                type="file",
                                value=relative_path,
                                title="PPT 演示文稿",
                                description="自动生成的 PPT 文件",
                            )
                        )
                        await db.commit()
                except Exception as e:
                    logger.error(f"Failed to save ppt artifact: {e}")
            results.append({
                "tool_call_id": tool_call["id"],
                "role": "tool",
                "name": tool_call["name"],
                "content": str(tool_output)
            })
            
    return {"messages": results}

def route_next(state: PPTGeneratorState):
    """
    决定下一步：是有工具调用还是结束
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tools"
    return END

# 构建图
workflow = StateGraph(PPTGeneratorState)

workflow.add_node("load_skills", skill_injector.load_skills_context)
workflow.add_node("analyze_and_generate", analyze_and_generate)
workflow.add_node("execute_tools", execute_tools)

workflow.set_entry_point("load_skills")
workflow.add_edge("load_skills", "analyze_and_generate")

workflow.add_conditional_edges(
    "analyze_and_generate",
    route_next,
    {
        "execute_tools": "execute_tools",
        END: END
    }
)

workflow.add_edge("execute_tools", "analyze_and_generate") # 工具执行完后回传给 LLM 总结

app = workflow.compile()
