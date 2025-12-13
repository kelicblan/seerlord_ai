import asyncio
import sys
import shutil
import json
from typing import Dict, List, Optional, Any, Type
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.tools import BaseTool, StructuredTool
from loguru import logger
from pydantic import create_model, Field
from tenacity import retry, stop_after_attempt, wait_exponential

class MCPManager:
    """
    Manages connections to MCP servers and exposes their tools.
    """
    def __init__(self):
        self._exit_stack = AsyncExitStack()
        self._sessions: Dict[str, ClientSession] = {}
        self._tools: Dict[str, List[BaseTool]] = {}

    async def load_config(self, config_path: str = "mcp.json"):
        """
        Loads MCP servers from a configuration file.
        """
        import os
        
        if not os.path.exists(config_path):
            logger.warning(f"MCP config file not found: {config_path}")
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            servers = config.get("mcpServers", {})
            for name, server_config in servers.items():
                command = server_config.get("command")
                args = server_config.get("args", [])
                env = server_config.get("env") # Optional env vars
                
                # Handle relative paths for python scripts if needed
                # If command is python and first arg ends with .py, make it absolute
                if command == "python" and args and args[0].endswith(".py"):
                    # Assuming relative to CWD (project root)
                    if not os.path.isabs(args[0]):
                        args[0] = os.path.abspath(args[0])

                try:
                    await self.connect_to_server(name, command, args, env)
                except Exception as e:
                    logger.error(f"Failed to connect to MCP server {name}: {e}")
                    # Continue loading other servers
                
        except Exception as e:
            logger.error(f"Failed to load MCP config from {config_path}: {e}")

    async def connect_to_server(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        """
        Connects to an MCP server via stdio.
        """
        logger.info(f"Connecting to MCP server '{name}' via command: {command} {args}")
        
        # Use sys.executable if command is 'python' to ensure we use the same venv
        if command == 'python':
            import sys
            executable = sys.executable
        else:
            executable = shutil.which(command) or command

        server_params = StdioServerParameters(
            command=executable,
            args=args,
            env=env
        )

        try:
            # Create the connection context
            # stdio_client returns (read_stream, write_stream)
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            
            # Create the session
            session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            
            # Initialize session
            await session.initialize()
            
            self._sessions[name] = session
            logger.info(f"Successfully connected to MCP server: {name}")
            
            # Load tools immediately
            await self._load_tools(name, session)
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server '{name}': {e}")
            raise

    def _json_schema_to_pydantic(self, schema: Dict[str, Any], model_name: str) -> Type:
        """
        Convert a JSON schema to a Pydantic model dynamically.
        """
        fields = {}
        if "properties" in schema:
            for field_name, field_schema in schema["properties"].items():
                field_type = str
                if field_schema.get("type") == "integer":
                    field_type = int
                elif field_schema.get("type") == "number":
                    field_type = float
                elif field_schema.get("type") == "boolean":
                    field_type = bool
                elif field_schema.get("type") == "array":
                    field_type = list
                elif field_schema.get("type") == "object":
                    field_type = dict
                
                # Check if required
                is_required = field_name in schema.get("required", [])
                default = ... if is_required else None
                
                fields[field_name] = (field_type, Field(default, description=field_schema.get("description", "")))
        
        return create_model(model_name, **fields)

    async def _load_tools(self, server_name: str, session: ClientSession):
        """
        List tools from the session and convert them to LangChain tools.
        """
        result = await session.list_tools()
        tools = []
        
        for mcp_tool in result.tools:
            tool_name = mcp_tool.name
            tool_desc = mcp_tool.description or ""
            input_schema = mcp_tool.inputSchema or {}
            
            # Convert JSON Schema to Pydantic Model for validation and LLM introspection
            args_schema = self._json_schema_to_pydantic(input_schema, f"{tool_name}_Input")
            
            # Create a LangChain StructuredTool
            # We need to capture server_name and tool_name in the closure
            @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
            async def _tool_func(**kwargs):
                try:
                    result = await session.call_tool(tool_name, arguments=kwargs)
                    # Extract text content for LangChain compatibility
                    if hasattr(result, 'content') and isinstance(result.content, list):
                        texts = []
                        for item in result.content:
                            if hasattr(item, 'type') and item.type == 'text' and hasattr(item, 'text'):
                                texts.append(item.text)
                        if texts:
                            return "\n".join(texts)
                    return str(result)
                except Exception as e:
                    logger.error(f"Error calling MCP tool {tool_name}: {e}")
                    raise e

            lc_tool = StructuredTool.from_function(
                func=None,
                coroutine=_tool_func,
                name=tool_name,
                description=tool_desc,
                args_schema=args_schema
            )
            tools.append(lc_tool)
            
        self._tools[server_name] = tools
        logger.info(f"Loaded {len(tools)} tools from server '{server_name}'")

    def get_tool(self, server_name: str, tool_name: str) -> Optional[BaseTool]:
        """
        Retrieve a specific tool by name from a server.
        """
        if server_name not in self._tools:
            return None
        for tool in self._tools[server_name]:
            if tool.name == tool_name:
                return tool
        return None

    def get_all_tools(self, server_name: str = None) -> List[BaseTool]:
        """
        Get tools. If server_name is provided, return tools for that server.
        Otherwise return all tools flattened.
        """
        if server_name:
            return self._tools.get(server_name, [])
        
        all_tools = []
        for tools in self._tools.values():
            all_tools.extend(tools)
        return all_tools

    async def close_all(self):
        """
        Close all sessions and the exit stack.
        """
        logger.info("Closing all MCP sessions...")
        await self._exit_stack.aclose()
        self._sessions.clear()
        self._tools.clear()

    def get_status_summary(self) -> Dict[str, Any]:
        """
        Returns a summary of connected MCP servers and tools.
        """
        servers_info = []
        total_tools = 0
        
        for name, session in self._sessions.items():
            tool_count = len(self._tools.get(name, []))
            total_tools += tool_count
            servers_info.append({
                "name": name,
                "status": "connected", # If it's in _sessions, it's connected
                "tool_count": tool_count
            })
            
        return {
            "servers": servers_info,
            "total_servers": len(self._sessions),
            "total_tools": total_tools
        }

    async def close(self):
        """
        Close all connections.
        """
        await self.close_all()

# Global Singleton
mcp_manager = MCPManager()
