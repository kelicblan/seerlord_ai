from typing import TypedDict, Annotated, Sequence, Optional, List
import operator
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langchain_core.runnables import RunnableConfig

from server.core.llm import get_llm
from .tools import send_system_email
from server.kernel.skill_integration import skill_injector

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    tenant_id: Optional[str]
    user_id: Optional[str]
    skills_context: Optional[str]
    used_skill_ids: Optional[List[str]]

def get_system_message(skills: str = ""):
    content = """You are the Mail Service Agent.
Your primary responsibility is to send emails using the `send_system_email` tool.
When an application agent calls you, they are the recipient. You need their Agent ID to look up their email address in the configuration.
If the Agent ID is not explicitly provided in the message, ask for it, or try to infer it if context permits.
The `target_agent_id` parameter in the tool corresponds to the Agent ID of the application (e.g., 'news_reporter').
"""
    if skills:
        content += f"\n[Expert Guidelines]:\n{skills}\n"
        
    return SystemMessage(content=content)

tools = [send_system_email]
llm = get_llm()
llm_with_tools = llm.bind_tools(tools)

async def agent_node(state: AgentState, config: RunnableConfig):
    skills = state.get("skills_context", "")
    messages = [get_system_message(skills)] + list(state["messages"])
    response = await llm_with_tools.ainvoke(messages, config)
    return {"messages": [response]}

workflow = StateGraph(AgentState)
workflow.add_node("load_skills", skill_injector.load_skills_context)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))

workflow.set_entry_point("load_skills")
workflow.add_edge("load_skills", "agent")

def should_continue(state):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

app = workflow.compile()
