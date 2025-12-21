from typing import Dict, List, Any, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, BaseMessage
from loguru import logger
import operator

from langchain_core.runnables import RunnableConfig
from server.config_engine.loader import ConfigLoader, AgentConfig, TaskConfig
from server.core.llm import get_llm

class AgentState(TypedDict, total=False):
    results: Annotated[Dict[str, str], lambda x, y: {**x, **y}]  # TaskID -> Output mapping (Merge strategy)
    input: str # User input/goal
    messages: List[BaseMessage] # Support standard messages input
    language: str # Support language preference

class AgentBuilder:
    def __init__(self, agents_path: str, tasks_path: str):
        self.loader = ConfigLoader()
        self.agents_config = self.loader.load_agents(agents_path)
        self.tasks_config = self.loader.load_tasks(tasks_path)
        
    def _create_node_func(self, task: TaskConfig, agent: AgentConfig):
        """
        Creates a closure for the node execution function.
        """
        async def node_func(state: AgentState, config: RunnableConfig):
            logger.info(f"🚀 Executing Task: {task.id} by Agent: {agent.role}")
            
            # 1. Build Context from previous results
            context_str = ""
            current_results = state.get("results", {})
            if task.context:
                context_str = "\n\n### Context from previous tasks:\n"
                for ctx_id in task.context:
                    result = current_results.get(ctx_id, "No result found.")
                    context_str += f"- Task {ctx_id}: {result}\n"
            
            # 2. Build Prompt
            # Handle Input Extraction (Support both 'input' string and 'messages' list)
            user_input = state.get("input", "")
            if not user_input and state.get("messages"):
                # Extract last human message content
                msgs = state.get("messages")
                # Handle dicts or objects
                for m in reversed(msgs):
                    if isinstance(m, dict):
                        if m.get("type") == "human":
                            user_input = m.get("content")
                            break
                    elif hasattr(m, "type") and m.type == "human":
                        user_input = m.content
                        break
                    elif isinstance(m, HumanMessage):
                         user_input = m.content
                         break

            # Handle Language
            language = state.get("language", "zh-CN")
            # Also check if language instruction is in messages (from middleware)
            lang_instruction = ""
            if language == "en":
                lang_instruction = "IMPORTANT: Please respond in English."
            elif language == "zh-TW":
                lang_instruction = "IMPORTANT: Please respond in Traditional Chinese (繁体中文)."
            else:
                lang_instruction = "IMPORTANT: Please respond in Simplified Chinese (简体中文)."

            # Override if middleware injected system message
            if state.get("messages"):
                 msgs = state.get("messages")
                 if msgs and isinstance(msgs[0], dict) and msgs[0].get("type") == "system" and "IMPORTANT" in msgs[0].get("content", ""):
                     lang_instruction = msgs[0].get("content")

            system_prompt = (
                f"You are {agent.role}.\n"
                f"Goal: {agent.goal}\n"
                f"Backstory: {agent.backstory}\n"
                f"{lang_instruction}\n"
            )
            
            user_prompt = (
                f"User Input: {user_input}\n\n"
                f"Task Description: {task.description}\n"
                f"Expected Output: {task.expected_output}\n"
                f"{context_str}\n"
                f"Please execute the task."
            )
            
            # 3. Call LLM with Tool Support
            llm = get_llm(temperature=0.7) 
            
            tools = []
            if agent.tools:
                from server.kernel.mcp_manager import mcp_manager
                # Flatten all available tools to find matches
                all_tools = mcp_manager.get_all_tools()
                for tool_name in agent.tools:
                    # Find tool by name
                    found = next((t for t in all_tools if t.name == tool_name), None)
                    if found:
                        tools.append(found)
                    else:
                        logger.warning(f"Tool '{tool_name}' not found in MCP Manager.")
            
            if tools:
                llm = llm.bind_tools(tools)
                
            messages: List[BaseMessage] = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            final_content = ""
            # ReAct Loop (Max 5 steps)
            for _ in range(5):
                # Use astream to enable streaming events for the frontend
                response = None
                async for chunk in llm.astream(messages, config=config):
                    if not response:
                        response = chunk
                    else:
                        response += chunk
                
                messages.append(response)
                
                if not response.tool_calls:
                    final_content = response.content
                    break
                
                # Execute tools
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    args = tool_call["args"]
                    tool_id = tool_call["id"]
                    
                    logger.info(f"🛠️ Agent {agent.role} calling tool: {tool_name}")
                    
                    # Find the tool again
                    selected_tool = next((t for t in tools if t.name == tool_name), None)
                    if selected_tool:
                        try:
                            # Tool execution
                            tool_result = await selected_tool.ainvoke(args, config=config)
                        except Exception as e:
                            tool_result = f"Error executing tool: {e}"
                    else:
                        tool_result = f"Tool {tool_name} not found."
                        
                    messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_id))
            else:
                # Loop finished without breaking (max steps reached)
                if messages and hasattr(messages[-1], 'content'):
                     final_content = str(messages[-1].content)
                else:
                     final_content = "Max execution steps reached without final answer."
            
            logger.info(f"✅ Task {task.id} Completed.")
            
            # 4. Return update for State
            return {"results": {task.id: str(final_content)}}
            
        return node_func

    def build(self):
        workflow = StateGraph(AgentState)
        
        # 1. Add Nodes
        previous_node_id = None
        first_node_id = None
        
        for task in self.tasks_config:
            agent = self.agents_config.get(task.agent)
            if not agent:
                raise ValueError(f"Agent '{task.agent}' not found in configuration.")
            
            node_id = task.id
            node_func = self._create_node_func(task, agent)
            
            workflow.add_node(node_id, node_func)
            
            # 2. Add Edges (Sequential for now)
            if previous_node_id:
                workflow.add_edge(previous_node_id, node_id)
            else:
                first_node_id = node_id
                
            previous_node_id = node_id
            
        # 3. Set Entry and End
        if first_node_id:
            workflow.set_entry_point(first_node_id)
            workflow.add_edge(previous_node_id, END)
            
        return workflow.compile()
