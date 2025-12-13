from typing import Annotated, List, Dict, Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from pydantic import BaseModel, Field
from server.core.config import settings
from server.core.llm import get_llm
from .schema import TutorialSchema

# 定义局部状态
class TutorialState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    tutorial_result: Optional[TutorialSchema]
    critique_count: int
    score: int
    critique_feedback: str

# Define Structured Output for Critique
class CritiqueResult(BaseModel):
    score: int = Field(description="Score from 1 to 10. 10 is perfect.")
    critique: str = Field(description="Detailed critique of the tutorial outline.")
    suggestions: str = Field(description="Specific suggestions for improvement.")

def analyze_intent(state: TutorialState):
    """
    分析用户意图节点。
    目前这个节点主要充当透传和简单的上下文准备，
    在更复杂的场景中，可以用于提取关键参数（主题、难度等）。
    """
    # 可以在这里做一些预处理，例如总结用户需求
    # 暂时直接透传，因为 generate_outline 会处理主要逻辑
    return {"messages": [SystemMessage(content="Analyzing user request for tutorial generation...")]}

def generate_outline(state: TutorialState):
    """
    生成教程大纲节点。
    使用结构化输出生成 TutorialSchema。
    """
    try:
        from loguru import logger
        llm = get_llm(temperature=0.7)
        
        structured_llm = llm.with_structured_output(TutorialSchema, include_raw=True)
        
        base_prompt = (
            "You are an expert curriculum designer. "
            "Create a structured tutorial outline based on the user's request. "
            "Ensure the difficulty level matches the user's expertise if specified."
        )
        
        # Check for critique feedback
        critique_feedback = state.get("critique_feedback", "")
        
        # 提取全局反馈历史
        messages_list = state.get("messages", [])
        feedback_history = []
        for msg in reversed(messages_list):
            if hasattr(msg, 'content') and "[Critic Feedback]" in msg.content:
                feedback_history.append(msg.content)
                if len(feedback_history) >= 2: break
                
        if feedback_history:
            critique_feedback += "\n".join(feedback_history)

        if critique_feedback:
            system_prompt = (
                f"{base_prompt}\n\n"
                f"Previous critique and suggestions:\n{critique_feedback}\n"
                "Please revise the tutorial outline to address these suggestions."
            )
            # When revising, we might want to include the previous result in context, 
            # but usually the LLM context window has the history if we pass 'messages'.
            # However, here we are generating a fresh structure.
        else:
            system_prompt = base_prompt
        
        # Construct messages. If revising, we should probably just use the system prompt + user request
        # But 'messages' in state accumulates.
        # Let's just append the new system instruction.
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
            
        # 调用 LLM 生成结构化数据
        result = structured_llm.invoke(messages)
        tutorial = result["parsed"]
        raw_msg = result["raw"]
        
        response_text = f"Generated Tutorial: {tutorial.title} ({tutorial.difficulty})\n"
        for i, mod in enumerate(tutorial.modules, 1):
            response_text += f"\nModule {i}: {mod.name}\n"
            for topic in mod.topics:
                response_text += f"  - {topic}\n"
        
        ai_msg = AIMessage(content=response_text, name="tutorial_agent")
        if hasattr(raw_msg, "usage_metadata"):
            ai_msg.usage_metadata = raw_msg.usage_metadata
            
        return {
            "tutorial_result": tutorial,
            "messages": [ai_msg]
        }
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error generating tutorial: {str(e)}", name="tutorial_agent")]}

def critique_node(state: TutorialState):
    """
    Critiques the generated tutorial.
    """
    tutorial = state.get("tutorial_result")
    if not tutorial:
        return {"critique_feedback": "No tutorial generated.", "score": 0}

    llm = get_llm(temperature=0.2)
    structured_llm = llm.with_structured_output(CritiqueResult)

    # Serialize tutorial for critique
    tutorial_str = f"Title: {tutorial.title}\nDifficulty: {tutorial.difficulty}\nSummary: {tutorial.summary}\nModules:\n"
    for mod in tutorial.modules:
        tutorial_str += f"- {mod.name}: {', '.join(mod.topics)}\n"

    prompt = (
        "You are a Senior Curriculum Reviewer.\n"
        "Review the following Tutorial Outline.\n"
        "Check for:\n"
        "1. Logical progression of topics.\n"
        "2. Appropriateness of difficulty level.\n"
        "3. Completeness and coverage.\n"
        "4. Clarity of module names and topics.\n\n"
        f"Tutorial Outline:\n{tutorial_str}"
    )

    try:
        result = structured_llm.invoke([SystemMessage(content=prompt)])
        score = result.score
        feedback = f"Score: {score}/10. Critique: {result.critique}. Suggestions: {result.suggestions}"
    except Exception as e:
        score = 10 # Fail open
        feedback = "Critique failed."

    return {
        "critique_feedback": feedback,
        "score": score,
        "critique_count": state.get("critique_count", 0) + 1
    }

def should_revise(state: TutorialState):
    """
    Decides whether to revise or finish.
    """
    score = state.get("score", 0)
    count = state.get("critique_count", 0)
    
    if score >= 8 or count >= 3:
        return "end"
    return "revise"

# 构建子图
workflow = StateGraph(TutorialState)

workflow.add_node("analyze_intent", analyze_intent)
workflow.add_node("generate_outline", generate_outline)
workflow.add_node("critique_tutorial", critique_node)

workflow.set_entry_point("analyze_intent")
workflow.add_edge("analyze_intent", "generate_outline")
workflow.add_edge("generate_outline", "critique_tutorial")

workflow.add_conditional_edges(
    "critique_tutorial",
    should_revise,
    {
        "revise": "generate_outline",
        "end": END
    }
)

tutorial_graph = workflow.compile()
