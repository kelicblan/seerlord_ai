import importlib
import inspect
from typing import Dict, Type
from pathlib import Path
import sys

from loguru import logger

from server.kernel.interface import AgentPlugin
from server.core.config import settings

class PluginRegistry:
    """
    插件注册表（单例模式）。
    负责扫描、加载和管理所有的代理插件。
    """
    _instance = None
    _plugins: Dict[str, AgentPlugin] = {}
    _plugin_dirs: Dict[str, str] = {} # Map plugin ID to directory name
    _loaded_modules: set = set()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PluginRegistry, cls).__new__(cls)
        return cls._instance

    @property
    def plugins(self) -> Dict[str, AgentPlugin]:
        """获取所有已注册的插件"""
        return self._plugins

    def scan_and_load(self):
        """
        扫描插件目录并加载所有实现的 AgentPlugin。
        """
        # 使用项目根目录计算绝对路径
        # 假设当前工作目录是项目根目录，或者通过 settings.PLUGIN_DIR 计算
        plugin_path = Path(settings.PLUGIN_DIR).resolve()
        
        if not plugin_path.exists():
            logger.warning(f"插件目录不存在: {plugin_path}")
            return

        logger.info(f"开始扫描插件目录: {plugin_path}")
        
        # 确保项目根目录在 sys.path 中，以便可以导入 server.plugins
        project_root = Path.cwd()
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        # 基础包名
        base_package = settings.PLUGIN_DIR.replace("/", ".").replace("\\", ".")
        
        for item in plugin_path.iterdir():
            # 忽略 __pycache__，但允许 _ 开头的插件目录（如 _example_agent 或 _system_agent_）
            if item.is_dir() and item.name != "__pycache__":
                plugin_pkg_name = item.name
                
                # 尝试加载模块
                module_names_to_try = [
                    f"{base_package}.{plugin_pkg_name}",          # 包导入 (init)
                    f"{base_package}.{plugin_pkg_name}.plugin"   # 显式文件导入
                ]
                
                loaded = False
                for module_name in module_names_to_try:
                    if module_name in self._loaded_modules:
                        continue
                        
                    try:
                        logger.debug(f"尝试加载模块: {module_name}")
                        module = importlib.import_module(module_name)
                        if self._register_plugins_from_module(module, plugin_pkg_name):
                            self._loaded_modules.add(module_name)
                            loaded = True
                            # 如果在包级别找到了，就不需要再找 plugin.py 了，或者继续找以防万一
                            # 这里策略是：只要找到至少一个插件，就算成功
                    except ImportError as e:
                        # 忽略特定的子模块不存在错误，但记录其他导入错误
                        if f"No module named '{module_name}'" not in str(e) and \
                           f"No module named '{module_name.split('.')[-1]}'" not in str(e):
                             logger.error(f"导入模块 {module_name} 失败: {e}")
                    except Exception as e:
                        logger.exception(f"加载模块 {module_name} 时发生意外错误: {e}")

    def _register_plugins_from_module(self, module, plugin_dir_name: str) -> bool:
        """
        从模块中查找并注册 AgentPlugin 的子类。
        返回是否发现了插件。
        """
        found = False
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, AgentPlugin) and 
                obj is not AgentPlugin):
                
                try:
                    # 检查是否已经注册过该类型的实例（可选，取决于是否允许同一类多实例）
                    # 这里我们简单地每次实例化并注册，依赖 register 方法的覆盖逻辑
                    plugin_instance = obj()
                    self.register(plugin_instance, plugin_dir_name)
                    found = True
                except Exception as e:
                    logger.exception(f"实例化插件类 {name} 失败: {e}")
        return found

    def register(self, plugin: AgentPlugin, dir_name: str = None):
        """
        注册单个插件实例。
        """
        if plugin.name in self._plugins:
            logger.warning(f"插件 {plugin.name} 已存在，将被覆盖。")
        
        self._plugins[plugin.name] = plugin
        if dir_name:
            self._plugin_dirs[plugin.name] = dir_name
            
        logger.success(f"已注册插件: {plugin.name} ({plugin.description})")

    def get_plugin(self, name: str) -> AgentPlugin:
        """根据名称获取插件"""
        return self._plugins.get(name)

    def get_plugin_dir(self, name: str) -> str:
        """根据插件名称获取对应的目录名"""
        return self._plugin_dirs.get(name)

# 创建全局单例实例
registry = PluginRegistry()
