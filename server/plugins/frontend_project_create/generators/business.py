"""业务逻辑生成器：为每个模块生成 Pinia store 和 composable。"""
from typing import Dict, List

from .base import BaseGenerator, GenerationResult, GenerationContext
from ._utils import normalize_module_name, normalize_type_name
from ..memory.short_term import ShortTermMemory


class BusinessLogicGenerator(BaseGenerator):
    async def generate(
        self,
        session: ShortTermMemory,
        context: GenerationContext,
    ) -> GenerationResult:
        try:
            files = {}
            modules = context.coverage_matrix.get_all_modules()

            for module in modules:
                # 规范化模块名（移除连字符）
                normalized_module = normalize_module_name(module)
                normalized_type = normalize_type_name(module.title())
                
                store_file = f"src/stores/{normalized_module}.ts"
                files[store_file] = self._generate_store(module)

                composable_file = f"src/composables/use{normalized_type}.ts"
                files[composable_file] = self._generate_composable(module)

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

    def _generate_store(self, module: str) -> str:
        # 规范化模块名
        normalized_module = normalize_module_name(module)
        normalized_type = normalize_type_name(module.title())

        auth_block = ""
        if normalized_module == "auth":
            auth_block = (
                "\n"
                "  store.logout = function() {\n"
                "    localStorage.removeItem('token')\n"
                "    window.location.href = '/login'\n"
                "  }\n"
                "  store.userName = computed(() => {\n"
                "    const user = store.currentItem as any\n"
                "    return user?.nickname || user?.username || 'User'\n"
                "  })\n"
                "  store.isAuthenticated = computed(() => !!localStorage.getItem('token'))\n"
            )

        tpl = (
            f"import {{ defineStore }} from 'pinia'\n"
            f"import {{ ref, computed }} from 'vue'\n"
            f"import type {{ {normalized_type}Item, {normalized_type}ListParams }} from '@/types/{normalized_module}'\n"
            "export type LoginParams = { username: string; password: string }\n"
            "export type LoginPayload = { username: string; password: string; captcha?: string; rememberMe?: boolean }\n"
            "\n"
            f"import {{ {normalized_module}Api }} from '@/api/{normalized_module}'\n"
            "\n"
            f"export const use{normalized_type}Store = defineStore('{normalized_module}', () => {{\n"
            "\n"
            f"  const list = ref<{normalized_type}Item[]>([])\n"
            "  const total = ref(0)\n"
            "  const loading = ref(false)\n"
            f"  const currentItem = ref<{normalized_type}Item | null>(null)\n"
            "\n"
            "  const hasMore = computed(() => list.value.length < total.value)\n"
            "\n"
            f"  async function fetchList(params: {normalized_type}ListParams) {{\n"
            "    loading.value = true\n"
            "    try {\n"
            f"      const res = await {normalized_module}Api.list(params)\n"
            "      list.value = res.data.list\n"
            "      total.value = res.data.total\n"
            "    } finally {\n"
            "      loading.value = false\n"
            "    }\n"
            "  }\n"
            "\n"
            "  async function fetchDetail(id: string) {\n"
            "    loading.value = true\n"
            "    try {\n"
            f"      const res = await {normalized_module}Api.detail(id)\n"
            "      currentItem.value = res.data\n"
            "    } finally {\n"
            "      loading.value = false\n"
            "    }\n"
            "  }\n"
            "\n"
            f"  async function create(data: Partial<{normalized_type}Item>) {{\n"
            f"    await {normalized_module}Api.create(data)\n"
            "    await fetchList({ page: 1 })\n"
            "  }\n"
            "\n"
            f"  async function update(id: string, data: Partial<{normalized_type}Item>) {{\n"
            f"    await {normalized_module}Api.update(id, data)\n"
            "    await fetchList({ page: 1 })\n"
            "  }\n"
            "\n"
            f"  async function remove(id: string) {{\n"
            f"    await {normalized_module}Api.delete(id)\n"
            "    await fetchList({ page: 1 })\n"
            "  }\n"
            "\n"
            "  function reset() {\n"
            "    list.value = []\n"
            "    total.value = 0\n"
            "    currentItem.value = null\n"
            "  }\n"
            "\n"
            "  const store: any = {\n"
            "    list,\n"
            "    total,\n"
            "    loading,\n"
            "    currentItem,\n"
            "    hasMore,\n"
            "    fetchList,\n"
            "    fetchDetail,\n"
            "    create,\n"
            "    update,\n"
            "    remove,\n"
            "    reset,\n"
            "  }" + auth_block + "\n"
            "\n"
            "  return store\n"
            "})\n"
        )
        return tpl

    def _generate_composable(self, module: str) -> str:
        # 规范化模块名
        normalized_module = normalize_module_name(module)
        normalized_type = normalize_type_name(module.title())

        tpl = (
            f"import {{ storeToRefs }} from 'pinia'\n"
            f"import {{ use{normalized_type}Store }} from '@/stores/{normalized_module}'\n"
            "import { computed, ref } from 'vue'\n"
            "\n"
            f"export function use{normalized_type}() {{\n"
            f"  const store = use{normalized_type}Store()\n"
            "  const { list, total, loading, currentItem, hasMore } = storeToRefs(store)\n"
            "\n"
            "  const selectedIds = ref<string[]>([])\n"
            "\n"
            "  async function loadList(params?: any) {\n"
            "    await store.fetchList(params)\n"
            "  }\n"
            "\n"
            "  async function loadDetail(id: string) {\n"
            "    await store.fetchDetail(id)\n"
            "  }\n"
            "\n"
            "  async function handleCreate(data: any) {\n"
            "    await store.create(data)\n"
            "  }\n"
            "\n"
            "  async function handleUpdate(id: string, data: any) {\n"
            "    await store.update(id, data)\n"
            "  }\n"
            "\n"
            "  async function handleDelete(id: string) {\n"
            "    await store.remove(id)\n"
            "  }\n"
            "\n"
            "  function toggleSelect(id: string) {\n"
            "    const index = selectedIds.value.indexOf(id)\n"
            "    if (index > -1) {\n"
            "      selectedIds.value.splice(index, 1)\n"
            "    } else {\n"
            "      selectedIds.value.push(id)\n"
            "    }\n"
            "  }\n"
            "\n"
            "  function clearSelection() {\n"
            "    selectedIds.value = []\n"
            "  }\n"
            "\n"
            "  return {\n"
            "    list,\n"
            "    total,\n"
            "    loading,\n"
            "    currentItem,\n"
            "    hasMore,\n"
            "    selectedIds,\n"
            "    loadList,\n"
            "    loadDetail,\n"
            "    handleCreate,\n"
            "    handleUpdate,\n"
            "    handleDelete,\n"
            "    toggleSelect,\n"
            "    clearSelection,\n"
            "  }\n"
            "}\n"
        )
        return tpl
