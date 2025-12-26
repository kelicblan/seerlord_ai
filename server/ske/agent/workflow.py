import json
from typing import Dict, Any, List

from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from loguru import logger

from server.ske.agent.state import SkeAgentState
from server.ske.search import SkeSearchService
from server.ske.llm_setup import initialize_ske_llm
from llama_index.core.llms import ChatMessage, MessageRole

# Initialize LLM settings (ensure they are loaded)
initialize_ske_llm()

# We need to bridge LlamaIndex LLM to LangChain or use LlamaIndex directly.
# Since the project rules mention LangGraph (LangChain ecosystem) but we set up LlamaIndex LLM in Task 2/3.
# To allow LangGraph to use the LLM configured in llm_setup (which puts it in Settings.llm), 
# we can access Settings.llm directly.

from llama_index.core import Settings

async def retrieve_node(state: SkeAgentState) -> Dict[str, Any]:
    """
    Node: Retrieve context from Neo4j Hybrid Search.
    """
    question = state["question"]
    logger.info(f"Agent retrieving context for: {question}")
    
    try:
        results = await SkeSearchService.search(question, top_k=5)
        
        # Format context
        context_list = []
        serialized_results = []
        
        for item in results:
            content = f"[{item.type}] {item.content}"
            if item.score:
                content += f" (Score: {item.score:.2f})"
            context_list.append(content)
            
            # Serialize for state
            serialized_results.append({
                "type": item.type,
                "content": item.content,
                "score": item.score,
                "metadata": item.metadata
            })
            
        return {
            "context": context_list,
            "search_results": serialized_results
        }
        
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        return {"context": [], "search_results": []}

async def generate_node(state: SkeAgentState) -> Dict[str, Any]:
    """
    Node: Generate answer using LLM and context.
    """
    question = state["question"]
    context = state["context"]
    
    context_str = "\n\n".join(context)
    
    system_prompt = (
        "You are SeerLord AI's Knowledge Engine Assistant.\n"
        "Answer the user's question based strictly on the provided Context.\n"
        "If the answer is not in the context, say you don't know.\n"
        "Cite specific entities or documents where possible.\n\n"
        "Context:\n"
        f"{context_str}"
    )
    
    # Use the LlamaIndex LLM wrapper configured in Settings.llm
    llm = Settings.llm
    
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
        ChatMessage(role=MessageRole.USER, content=question)
    ]
    
    logger.info("Agent generating answer...")
    response = await llm.achat(messages)
    
    return {"answer": response.message.content}

def build_ske_agent():
    """
    Construct the LangGraph workflow.
    """
    workflow = StateGraph(SkeAgentState)
    
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)
    
    workflow.set_entry_point("retrieve")
    
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    
    return workflow.compile()

# Singleton instance
ske_agent = build_ske_agent()
