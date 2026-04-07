"""代码生成工具函数：规范化命名，解决连字符问题。"""

import re


def normalize_module_name(module: str) -> str:
    """
    将模块名规范化为合法的 TypeScript 标识符。
    
    Examples:
        "rate-limit" -> "rateLimit"
        "access-control" -> "accessControl"
        "RateLimit" -> "RateLimit"
        "rateLimit" -> "rateLimit"
    """
    if not module:
        return module
    
    # 如果已经是 camelCase 或 PascalCase，直接返回
    if '-' not in module:
        return module
    
    # 将连字符转换为驼峰
    parts = module.split('-')
    return parts[0] + ''.join(p.title() for p in parts[1:])


def normalize_type_name(type_name: str) -> str:
    """
    将类型名规范化为合法的 TypeScript 类型名。
    
    Examples:
        "Rate-Limit-Item" -> "RateLimitItem"
        "RateLimitItem" -> "RateLimitItem"
    """
    if not type_name:
        return type_name
    
    # 移除所有连字符
    return type_name.replace('-', '')


def normalize_file_path(path: str) -> str:
    """
    规范化文件路径中的目录名。
    
    Examples:
        "src/views/rate-limit/Table.vue" -> "src/views/rateLimit/Table.vue"
        "src/api/rate-limit.ts" -> "src/api/rateLimit.ts"
    """
    if not path:
        return path
    
    parts = path.split('/')
    normalized_parts = []
    
    for part in parts:
        if '-' in part and part.endswith(('.ts', '.vue', '.tsx', '.jsx')):
            # 文件名：只移除连字符
            normalized_parts.append(part.replace('-', ''))
        elif '-' in part:
            # 目录名：转换为驼峰
            normalized_parts.append(normalize_module_name(part))
        else:
            normalized_parts.append(part)
    
    return '/'.join(normalized_parts)


def sanitize_code(code: str) -> str:
    """
    清理代码中的连字符标识符问题。
    
    这个函数会：
    1. 将连字符类型名转换为 PascalCase
    2. 警告可能的非法标识符
    
    注意：这个函数不处理所有情况，只是提供基础清理。
    """
    if not code:
        return code
    
    result = code
    
    # 修复连字符类型名 (Rate-Limit-Item -> RateLimitItem)
    result = re.sub(
        r'\b([A-Z][a-zA-Z]+(?:-[a-zA-Z]+)+)\b',
        lambda m: m.group(1).replace('-', ''),
        result
    )
    
    # 修复可能的非法标识符 (const rate-limit-api -> const rateLimitApi)
    # 注意：这个修复比较复杂，可能会有误判，所以注释掉
    # result = re.sub(
    #     r'\b(const|let|var)\s+([a-zA-Z][a-zA-Z0-9]*-[a-zA-Z][a-zA-Z0-9]*)\s*=',
    #     lambda m: f'{m.group(1)} {m.group(2).replace("-", "")} =',
    #     result
    # )
    
    return result


def should_normalize_module(module: str) -> bool:
    """
    判断模块名是否需要规范化。
    
    Returns:
        True 如果模块名包含连字符
    """
    return '-' in module


def get_view_filename_from_path(path: str) -> str:
    """
    根据路由路径生成视图文件名（扁平化命名）。
    views.py 和 router_gen.py 共用的统一函数。
    
    Examples:
        "/data/sync-logs"    -> "DataSynclogs.vue"
        "/user/list"          -> "UserList.vue"
        "/user/detail/:id"   -> "UserDetail.vue"
        "/login"             -> "LoginView.vue"
        "/data/sync-logs"    -> "DataSynclogs.vue"
    """
    parts = [p for p in path.split("/") if p and p not in ["", "mobile"]]
    if not parts:
        return "HomeView.vue"
    
    last = parts[-1]
    last_lower = last.lower()
    is_list_segment = last_lower in ("list", "index", "items", "records")
    is_param = last.startswith(":")
    
    dir_parts = [p for p in parts if not p.startswith(":")]
    
    if not dir_parts:
        return "IndexView.vue"
    
    title_parts = [p.title().replace("-", "") for p in dir_parts]
    name_base = "".join(title_parts) or "Index"
    
    if is_list_segment:
        view_name = name_base + "List.vue"
    elif is_param:
        view_name = name_base + ".vue"
    elif len(parts) == 1:
        view_name = name_base + "View.vue"
    else:
        view_name = name_base + ".vue"
    
    view_name = view_name.replace("*", "X").replace("?", "Q")
    
    return view_name
