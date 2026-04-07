"""路由生成器：根据 coverage_matrix 动态生成 Vue Router 路由配置。"""
from typing import Dict, List

from .base import BaseGenerator, GenerationResult, GenerationContext
from ._utils import get_view_filename_from_path
from ..memory.short_term import ShortTermMemory
from ..analyzers.structure import PageDefinition


class RouterGenerator(BaseGenerator):
    """根据 coverage_matrix 中的页面定义动态生成路由，并将路由注入到现有的 router/index.ts 文件中。"""

    async def generate(
        self,
        session: ShortTermMemory,
        context: GenerationContext,
    ) -> GenerationResult:
        try:
            router_path = "src/router/index.ts"
            constants_path = "src/constants/app.ts"
            existing = self._read_existing_router(context.project_path)
            new_router = self._generate_router(context.coverage_matrix.pages, existing)
            constants_content = self._generate_constants(context.coverage_matrix.pages)

            files = {
                router_path: new_router,
                constants_path: constants_content,
            }
            saved_files = self._save_files(files, context.project_path)
            return GenerationResult(
                success=True,
                files_generated=saved_files,
                files_content=files,
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return GenerationResult(success=False, error=str(e))

    def _read_existing_router(self, project_path: str) -> str:
        import os
        router_path = os.path.join(project_path, "src/router/index.ts")
        if os.path.exists(router_path):
            with open(router_path, encoding="utf-8", errors="replace") as f:
                return f.read()
        return ""

    def _get_component_name(self, page: PageDefinition) -> str:
        parts = [p for p in page.path.split("/") if p and p not in ["", "mobile"]]
        if not parts:
            return "Home"

        last = parts[-1]
        last_lower = last.lower()
        is_list_segment = last_lower in ("list", "index", "items", "records")
        is_param = last.startswith(":")

        content_parts = [p.title().replace("-", "") for p in parts if not p.startswith(":")]

        if is_list_segment:
            base = "".join(content_parts[:-1])
            return f"{base}List" if base else "List"
        elif is_param:
            base = "".join(content_parts)
            return base if base else "Detail"
        elif len(parts) == 1:
            return content_parts[0] + "View" if content_parts else "HomeView"
        else:
            return "".join(content_parts)

    def _get_view_filename(self, page: PageDefinition) -> str:
        """返回路由对应的视图文件名，与 ViewGenerator._get_view_paths 保持一致。
        
        使用共享的 get_view_filename_from_path 函数确保一致性。
        """
        return get_view_filename_from_path(page.path)

    def _generate_route_entry(self, page: PageDefinition) -> str:
        path = page.path.strip("/")
        view_filename = self._get_view_filename(page)
        component_import = f"@/views/{view_filename}"
        name = page.route_name.replace("-", " ").title().replace(" ", "")
        desc = (page.route_name or path.split("/")[-1]).replace("'", "\\'")
        requires_auth = "true" if page.module != "auth" else "false"

        return (
            f"    {{\n"
            f"      path: '/{path}',\n"
            f"      name: '{page.route_name}',\n"
            f"      component: () => import('{component_import}'),\n"
            f"      meta: {{\n"
            f"        title: '{name}',\n"
            f"        description: '{desc}',\n"
            f"        requiresAuth: {requires_auth},\n"
            f"      }},\n"
            f"    }},\n"
        )

    def _generate_router(self, pages: List[PageDefinition], existing: str) -> str:
        route_entries = []
        app_routes = []
        auth_routes = []

        for page in pages:
            route_entries.append(self._generate_route_entry(page))
            route_key = f"  '/{page.path.strip('/')}': '{page.route_name}',"
            if page.module == "auth":
                auth_routes.append(route_key)
            else:
                app_routes.append(route_key)

        if not route_entries:
            route_entries.append("    // No pages defined in coverage matrix")

        routes_block = "\n".join(route_entries)
        app_block = "\n".join(app_routes) if app_routes else "  // No app pages"
        auth_block = "\n".join(auth_routes) if auth_routes else "  // No auth pages"

        return (
            "import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'\n"
            "import { APP_TITLE } from '@/constants/app'\n"
            "\n"
            "const routes: RouteRecordRaw[] = [\n"
            + routes_block + "\n"
            "  {\n"
            "    path: '/:pathMatch(.*)*',\n"
            "    name: 'not-found',\n"
            "    component: () => import('@/views/NotFound.vue'),\n"
            "  },\n"
            "]\n"
            "\n"
            "const router = createRouter({\n"
            "  history: createWebHistory(),\n"
            "  routes,\n"
            "})\n"
            "\n"
            "router.beforeEach((to, _from, next) => {\n"
            "  const title = to.meta?.title as string\n"
            "  if (title) {\n"
            "    document.title = `${title} - ${APP_TITLE}`\n"
            "  }\n"
            "  next()\n"
            "})\n"
            "\n"
            "export const PAGE_ROUTES = {\n"
            + auth_block + "\n"
            "}\n"
            "\n"
            "export const APP_ROUTES = {\n"
            + app_block + "\n"
            "}\n"
            "\n"
            "export default router\n"
        )

    def _generate_constants(self, pages: List[PageDefinition]) -> str:
        auth_pages = [p for p in pages if p.module == "auth"]
        default_route = "/login" if auth_pages else (pages[0].path if pages else "/")
        login_route = next((p.path for p in pages if p.module == "auth"), "/login")
        return (
            "export const APP_TITLE = 'Generated Project'\n"
            "export const ACCESS_TOKEN_KEY = 'token'\n"
            "export const DEFAULT_ROUTE = '" + default_route + "'\n"
            "export const LOGIN_ROUTE = '" + login_route + "'\n"
            "export const REQUEST_TIMEOUT = 30000\n"
            "export const SUCCESS_CODE = 0\n"
        )
