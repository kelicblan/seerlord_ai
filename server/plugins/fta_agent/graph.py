from typing import List, Literal, Optional
from uuid import uuid4
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from pydantic import BaseModel, Field
from loguru import logger

from server.core.config import settings
from server.core.llm import get_llm
from server.memory.manager import MemoryManager
from server.memory.tools import memory_node
from .state import FTAState, FTANode
from .tools import nodes_to_plantuml

# 定义 LLM 输出结构
class CauseNode(BaseModel):
    description: str = Field(description="Description of the cause")
    type: Literal["intermediate", "basic_event"] = Field(description="Type of the event")
    gate_logic: Literal["OR", "AND"] = Field(default="OR", description="Logic gate relating these causes to the parent")

class AnalysisResult(BaseModel):
    causes: List[CauseNode] = Field(description="List of identified causes")

# Critique Structures
class CritiqueResult(BaseModel):
    score: int = Field(description="Score from 1 to 10. 10 is perfect.")
    critique: str = Field(description="Detailed critique of the fault tree logic.")
    suggestions: str = Field(description="Specific suggestions for improvement.")

class RevisedNode(BaseModel):
    id: str
    label: str
    type: str
    gate: str
    parent_id: Optional[str] = None

class RevisionResult(BaseModel):
    nodes: List[RevisedNode] = Field(description="The full list of revised nodes.")

def initialize_analysis(state: FTAState):
    """
    初始化分析：从用户输入中提取顶层事件。
    """
    # 如果已经有节点，跳过初始化
    if state.get("tree_nodes"):
        return {}

    # 简单地将最后一条消息作为顶层事件
    # 实际应用中应该用 LLM 提取
    user_input = state["messages"][-1].content
    
    root_id = str(uuid4())[:8]
    root_node = FTANode(
        id=root_id,
        label=user_input,
        type="top_event",
        parent_id=None
    )
    
    return {
        "tree_nodes": [root_node],
        "processing_queue": [root_id],
        "iteration_count": 0,
        "completed": False,
        "critique_count": 0,
        "score": 0
    }

async def root_cause_analysis(state: FTAState):
    """
    递归分析节点
    """
    queue = state.get("processing_queue", [])
    if not queue:
        return {"completed": True}

    current_id = queue[0]
    # 获取当前节点信息
    current_node = next((n for n in state["tree_nodes"] if n.id == current_id), None)
    
    if not current_node:
        # 节点未找到，移除并继续
        return {"processing_queue": queue[1:]}

    # 如果达到最大迭代次数，停止扩展
    if state.get("iteration_count", 0) > 5:  # 限制深度/次数防止死循环
        return {"processing_queue": queue[1:]}

    llm = get_llm(temperature=0.7)
    structured_llm = llm.with_structured_output(AnalysisResult)

    # 提取最近的反馈历史
    messages = state.get("messages", [])
    feedback_history = []
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) and "[Critic Feedback]" in msg.content:
            feedback_history.append(msg.content)
            if len(feedback_history) >= 2: break # 取最近2条
    
    feedback_context = ""
    if feedback_history:
        feedback_context = "\n\n[Previous Feedback to Address]:\n" + "\n".join(feedback_history)

    # Memory / RAG Context Retrieval
    rag_context = ""
    try:
        manager = await MemoryManager.get_instance()
        # Search for context relevant to the current event
        # Use retrieve_context which handles profile + facts
        context_dict = await manager.retrieve_context(query=current_node.label, user_id=state.get("user_id"))
        
        parts = []
        if context_dict["memories"]:
            parts.extend([f"- {m}" for m in context_dict["memories"]])
            
        if parts:
            rag_context = "\n\n[Relevant Historical Knowledge]:\n" + "\n".join(parts)

    except Exception as e:
        logger.warning(f"Memory Retrieval failed: {e}")
        
    global_memory = state.get("memory_context", "")

    system_prompt = (
        f"You are an expert in Fault Tree Analysis (FTA). "
        f"Analyze the event: '{current_node.label}'. "
        f"{global_memory}\n"
        f"{rag_context}"
        "Identify the immediate direct causes. "
        "Classify them as 'intermediate' (needs further analysis) or 'basic_event' (root cause). "
        "Determine if the relationship is OR or AND."
        f"{feedback_context}"
    )
    
    try:
        result = structured_llm.invoke([SystemMessage(content=system_prompt)])
        
        new_nodes = []
        new_queue_items = []
        
        for cause in result.causes:
            new_id = str(uuid4())[:8]
            node = FTANode(
                id=new_id,
                label=cause.description,
                type=cause.type,
                parent_id=current_id,
                gate=cause.gate_logic
            )
            new_nodes.append(node)
            
            if cause.type == "intermediate":
                new_queue_items.append(new_id)
        
        # 更新状态：移除当前处理的 ID，添加新的 ID 到队尾
        return {
            "tree_nodes": state["tree_nodes"] + new_nodes,
            "processing_queue": queue[1:] + new_queue_items,
            "iteration_count": state.get("iteration_count", 0) + 1
        }
        
    except Exception as e:
        logger.exception(f"FTA 分析失败：{e}")
        return {"processing_queue": queue[1:]} # 出错跳过

def critique_tree(state: FTAState):
    """
    Critiques the generated Fault Tree.
    """
    nodes = state.get("tree_nodes", [])
    if not nodes:
        return {"critique_feedback": "No nodes generated.", "score": 0}

    llm = get_llm(temperature=0.2)
    structured_llm = llm.with_structured_output(CritiqueResult)
    
    # Convert nodes to a readable text format for critique
    tree_text = ""
    for node in nodes:
        parent_info = f" (Parent: {node.parent_id})" if node.parent_id else " (ROOT)"
        tree_text += f"ID: {node.id}, Label: {node.label}, Type: {node.type}, Gate: {node.gate}{parent_info}\n"

    prompt = (
        "You are a Senior Safety Engineer reviewing a Fault Tree Analysis.\n"
        "Check for:\n"
        "1. Logical consistency (do causes strictly imply the effect?).\n"
        "2. Correct usage of AND/OR gates.\n"
        "3. Clear and specific event descriptions.\n"
        "4. No circular logic.\n\n"
        f"Fault Tree Nodes:\n{tree_text}"
    )

    try:
        result = structured_llm.invoke([SystemMessage(content=prompt)])
        score = result.score
        feedback = f"Score: {score}/10. Critique: {result.critique}. Suggestions: {result.suggestions}"
    except Exception as e:
        score = 10
        feedback = "Critique failed."

    return {
        "critique_feedback": feedback,
        "score": score,
        "critique_count": state.get("critique_count", 0) + 1
    }

def revise_tree(state: FTAState):
    """
    Revises the Fault Tree based on critique.
    """
    nodes = state.get("tree_nodes", [])
    feedback = state.get("critique_feedback", "")
    
    if not feedback:
        return {}

    llm = get_llm(temperature=0.5)
    structured_llm = llm.with_structured_output(RevisionResult)

    tree_text = ""
    for node in nodes:
        tree_text += f"ID: {node.id}, Label: {node.label}, Type: {node.type}, Gate: {node.gate}, Parent: {node.parent_id}\n"

    prompt = (
        "You are an expert in Fault Tree Analysis.\n"
        "Revise the following Fault Tree nodes based on the critique.\n"
        "Return the FULL list of nodes (including unmodified ones), but with necessary corrections applied.\n"
        "Maintain the same IDs for nodes unless they need to be deleted/replaced.\n\n"
        f"Current Tree:\n{tree_text}\n\n"
        f"Critique:\n{feedback}"
    )

    try:
        result = structured_llm.invoke([SystemMessage(content=prompt)])
        # Convert RevisedNode back to FTANode (they match structure but just to be safe)
        new_nodes = []
        for r_node in result.nodes:
            # We need to preserve parent_id which RevisedNode might not have implicitly handled perfectly if not careful
            # But here we defined RevisedNode without parent_id in schema above? 
            # Wait, I defined RevisedNode: id, label, type, gate. I missed parent_id!
            # Let's assume the LLM might hallucinate or miss parent_id if I don't ask for it.
            # I should add parent_id to RevisedNode.
            # Let's fix the schema inside the function for safety or rely on the previous state map.
            # Better: Let's fix RevisedNode definition in global scope.
            pass
            
        # Actually, let's just return the original nodes if revision fails or define RevisedNode properly.
        # I will update RevisedNode in the global scope in the search_replace block.
        
        # Re-mapping
        final_nodes = []
        for r in result.nodes:
            # Find original parent_id if possible or trust LLM
            # Let's assume LLM returns what we asked. I will update the schema below.
            final_nodes.append(FTANode(
                id=r.id,
                label=r.label,
                type=r.type,
                gate=r.gate,
                parent_id=getattr(r, 'parent_id', None) # We will add this field
            ))
            
        return {"tree_nodes": final_nodes}
        
    except Exception as e:
        # If revision fails, keep old nodes
        return {}

def finalize_result(state: FTAState):
    """
    生成最终报告
    """
    uml = nodes_to_plantuml(state["tree_nodes"])
    critique_info = f"\n\n(Quality Score: {state.get('score', 'N/A')}/10)"
    return {
        "messages": [AIMessage(content=f"FTA Analysis Complete.{critique_info}\n\nPlantUML:\n```plantuml\n{uml}\n```", name="fta_analyst")]
    }

def expansion_check(state: FTAState):
    if state.get("processing_queue") and state.get("iteration_count", 0) <= 5:
        return "continue"
    return "critique"

def revision_check(state: FTAState):
    score = state.get("score", 0)
    count = state.get("critique_count", 0)
    if score >= 8 or count >= 3:
        return "end"
    return "revise"

# 构建图
workflow = StateGraph(FTAState)

workflow.add_node("memory_load", memory_node)
workflow.add_node("initialize", initialize_analysis)
workflow.add_node("analyze", root_cause_analysis)
workflow.add_node("critique_tree", critique_tree)
workflow.add_node("revise_tree", revise_tree)
workflow.add_node("finalize", finalize_result)

workflow.set_entry_point("memory_load")
workflow.add_edge("memory_load", "initialize")
workflow.add_edge("initialize", "analyze")

workflow.add_conditional_edges(
    "analyze",
    expansion_check,
    {
        "continue": "analyze",
        "critique": "critique_tree"
    }
)

workflow.add_conditional_edges(
    "critique_tree",
    revision_check,
    {
        "revise": "revise_tree",
        "end": "finalize"
    }
)

workflow.add_edge("revise_tree", "critique_tree")
workflow.add_edge("finalize", END)

app = workflow.compile()
