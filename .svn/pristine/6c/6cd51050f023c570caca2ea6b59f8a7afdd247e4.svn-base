from typing import List
from .state import FTANode

def nodes_to_plantuml(nodes: List[FTANode]) -> str:
    """
    将 FTA 节点列表转换为 PlantUML 语法字符串。
    """
    if not nodes:
        return ""

    uml = "@startmindmap\n"
    uml += "skinparam monochrome true\n"
    
    # 构建树结构 map
    # id -> [children]
    tree_map = {}
    node_map = {}
    root_id = None
    
    for node in nodes:
        node_map[node.id] = node
        if node.parent_id is None:
            root_id = node.id
        else:
            if node.parent_id not in tree_map:
                tree_map[node.parent_id] = []
            tree_map[node.parent_id].append(node)
            
    if not root_id:
        return "No root node found"

    # 递归生成 PlantUML
    def _recruit_node(current_id, level=1):
        node = node_map.get(current_id)
        if not node:
            return ""
        
        indent = "*" * level
        line = f"{indent} {node.label}"
        if node.type == 'basic_event':
            line += " [Basic Event]"
        
        result = line + "\n"
        
        children = tree_map.get(current_id, [])
        for child in children:
            result += _recruit_node(child.id, level + 1)
            
        return result

    uml += _recruit_node(root_id)
    uml += "@endmindmap"
    
    return uml
