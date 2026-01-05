import asyncio
import sys
import shutil
import json
from typing import Dict, List, Optional, Any, Type, Tuple
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
        """
        MCP 管理器：负责读取配置、连接 MCP Server，并将其工具转换为 LangChain 工具。
        """
        self._exit_stack = AsyncExitStack()
        self._sessions: Dict[str, ClientSession] = {}
        self._tools: Dict[str, List[BaseTool]] = {}
        self._server_configs: Dict[str, Dict[str, Any]] = {}
        self._server_errors: Dict[str, str] = {}
        self._config_path: Optional[str] = None

    def get_status_summary(self) -> Dict[str, Any]:
        """
        返回所有 Server 的状态汇总，供前端展示。
        格式:
        {
            "servers": [
                {
                    "name": "filesystem",
                    "status": "connected", # connected, disconnected, error
                    "tool_count": 5,
                    "tools": [ ...tool_info... ],
                    "error": null
                }
            ]
        }
        """
        result = []
        
        # 1. 遍历所有配置中的 server（包括未连接的）
        all_servers = set(self._server_configs.keys())
        
        for name in all_servers:
            status = "disconnected"
            error = self._server_errors.get(name)
            tool_count = 0
            tools_info = []
            
            if name in self._sessions:
                status = "connected"
                # 获取该 server 下的所有 tools
                tools = self._tools.get(name, [])
                tool_count = len(tools)
                for t in tools:
                    tools_info.append({
                        "name": t.name,
                        "description": t.description,
                        "args_schema": t.args_schema.schema() if t.args_schema else {}
                    })
            
            if error:
                status = "error"

            result.append({
                "name": name,
                "status": status,
                "tool_count": tool_count,
                "tools": tools_info,
                "error": error,
                "config": self._server_configs.get(name, {})
            })
            
        total_servers = len(result)
        total_tools = sum(s["tool_count"] for s in result)

        return {
            "servers": result,
            "total_servers": total_servers,
            "total_tools": total_tools
        }

    def _resolve_config_path(self, config_path: str) -> Optional[str]:
        """
        解析 MCP 配置路径：
        - 先按原样/当前工作目录解析
        - 若不存在，回退到项目根目录（相对 server/ 目录推断）
        """
        import os

        if os.path.isabs(config_path) and os.path.exists(config_path):
            return config_path

        cwd_candidate = os.path.abspath(config_path)
        if os.path.exists(cwd_candidate):
            return cwd_candidate

        repo_root_candidate = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", config_path)
        )
        if os.path.exists(repo_root_candidate):
            return repo_root_candidate

        return None

    def _normalize_server_command_args(
        self, *, config_dir: str, command: Optional[str], args: List[str]
    ) -> Tuple[Optional[str], List[str]]:
        """
        规范化 server 的 command/args：
        - 将 python/node 的脚本参数（相对路径）按 config_dir 变为绝对路径
        """
        import os

        if not command:
            return command, args

        if not args:
            return command, args

        script_like = args[0]
        is_script = any(
            script_like.lower().endswith(ext) for ext in (".py", ".js", ".mjs", ".cjs")
        )
        if is_script and not os.path.isabs(script_like):
            args = list(args)
            args[0] = os.path.abspath(os.path.join(config_dir, script_like))

        return command, args

    def _resolve_executable(self, command: str) -> str:
        """
        解析可执行文件路径（兼容 Windows 的 *.cmd / *.exe）。
        """
        if command == "python":
            return sys.executable

        executable = shutil.which(command)
        if executable:
            return executable

        if sys.platform == "win32":
            for suffix in (".cmd", ".exe", ".bat"):
                alt = shutil.which(f"{command}{suffix}")
                if alt:
                    return alt

        return command

    async def load_config(self, config_path: str = "server/mcp.json"):
        """
        从配置文件加载 MCP servers，并尝试建立连接。
        注意：即使连接失败，也会把“已配置/失败原因”写入状态，便于前端展示与排障。
        """
        import os   

        resolved = self._resolve_config_path(config_path)
        if not resolved:
            logger.warning(f"MCP config file not found: {config_path}")
            return

        try:
            self._config_path = resolved
            config_dir = os.path.dirname(os.path.abspath(resolved))

            with open(resolved, "r", encoding="utf-8") as f:
                config = json.load(f)

            servers = config.get("mcpServers", {})
            if not isinstance(servers, dict):
                logger.error(f"Invalid MCP config format: mcpServers must be an object, got {type(servers)}")
                return

            self._server_configs = {k: v for k, v in servers.items() if isinstance(v, dict)}

            for name, server_config in self._server_configs.items():
                # Handle platform-specific overrides
                if "platforms" in server_config:
                    platform_overrides = server_config.get("platforms", {}).get(sys.platform, {})
                    if platform_overrides:
                        logger.info(f"Applying {sys.platform} overrides for server '{name}'")
                        # Override simple fields
                        for key in ["command", "args"]:
                            if key in platform_overrides:
                                server_config[key] = platform_overrides[key]
                        
                        # Merge env
                        if "env" in platform_overrides:
                            base_env = server_config.get("env") or {}
                            base_env.update(platform_overrides["env"])
                            server_config["env"] = base_env

                command = server_config.get("command")
                args = server_config.get("args", [])
                env = server_config.get("env")  # Optional env vars

                if not isinstance(args, list):
                    args = []

                # 关键：脚本路径以配置文件所在目录为基准，避免工作目录变化导致找不到文件
                command, args = self._normalize_server_command_args(
                    config_dir=config_dir, command=command, args=args
                )
                server_config["command"] = command
                server_config["args"] = args

                # 基础校验：脚本型 server 在连接前先校验入口文件是否存在，避免无意义的启动/报错
                if command in ("python", "node") and args:
                    entry = str(args[0])
                    if "{ABSOLUTE PATH" in entry.upper():
                        self._server_errors[name] = "入口脚本路径未配置（请替换为真实绝对路径）"
                        continue

                    if any(entry.lower().endswith(ext) for ext in (".py", ".js", ".mjs", ".cjs")):
                        if os.path.isabs(entry) and not os.path.exists(entry):
                            self._server_errors[name] = f"入口脚本不存在：{entry}"
                            continue

                try:
                    self._server_errors.pop(name, None)
                    await self.connect_to_server(name, command, args, env)
                except Exception as e:
                    err = str(e)
                    self._server_errors[name] = err
                    logger.error(f"Failed to connect to MCP server {name}: {err}")
                    # 继续加载其他 server，避免单点失败导致整体不可用

        except Exception as e:
            logger.error(f"Failed to load MCP config from {resolved}: {e}")

    async def connect_to_server(self, name: str, command: Optional[str], args: List[str], env: Optional[Dict[str, str]] = None):
        """
        通过 stdio 连接 MCP server。
        """
        if not command:
            raise ValueError("MCP server command is required")

        logger.info(f"Connecting to MCP server '{name}' via command: {command} {args}")
        
        executable = self._resolve_executable(command)

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
            # Using a factory function to properly capture the loop variable 'tool_name'
            def create_tool_executor(target_tool_name: str):
                @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
                async def _tool_func(**kwargs):
                    try:
                        result = await session.call_tool(target_tool_name, arguments=kwargs)
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
                        logger.error(f"Error calling MCP tool {target_tool_name}: {e}")
                        raise e
                return _tool_func

            lc_tool = StructuredTool.from_function(
                func=None,
                coroutine=create_tool_executor(tool_name),
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
        try:
            await self._exit_stack.aclose()
        except Exception as e:
            # Windows/AnyIO 下偶发出现异步生成器无法正常收敛的情况，这里降级为告警，避免影响服务退出
            logger.warning(f"Failed to close MCP sessions cleanly: {e}")
        self._sessions.clear()
        self._tools.clear()
        self._exit_stack = AsyncExitStack()

    async def close(self):
        """
        Close all connections.
        """
        await self.close_all()

# Global Singleton
mcp_manager = MCPManager()
