"""视图生成器：为每个页面定义生成完整可运行的 Vue 视图文件。"""
from typing import Dict, List

from .base import BaseGenerator, GenerationResult, GenerationContext
from ._utils import normalize_module_name, normalize_type_name, get_view_filename_from_path
from ..memory.short_term import ShortTermMemory
from ..analyzers.structure import PageDefinition


class ViewGenerator(BaseGenerator):
    """为 coverage_matrix 中的每个页面生成列表视图和详情视图。"""

    async def generate(
        self,
        session: ShortTermMemory,
        context: GenerationContext,
    ) -> GenerationResult:
        try:
            files: Dict[str, str] = {}
            pages = context.coverage_matrix.pages

            for page in pages:
                list_path, detail_path = self._get_view_paths(page)
                if list_path:
                    files[list_path] = self._generate_list_view(page)
                if self._has_detail_param(page.path) and detail_path:
                    files[detail_path] = self._generate_detail_view(page)

            files["src/views/NotFound.vue"] = self._generate_not_found()

            saved_files = self._save_files(files, context.project_path)
            return GenerationResult(
                success=True,
                files_generated=saved_files,
                files_content=files,
                metadata={"page_count": len(pages), "file_count": len(files)},
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return GenerationResult(success=False, error=str(e))

    def _get_view_paths(self, page: PageDefinition) -> tuple[str, str]:
        """根据页面路径生成扁平视图文件路径（与 RouterGenerator 一致）。

        使用共享的 get_view_filename_from_path 函数确保一致性。
        """
        parts = [p for p in page.path.split("/") if p and p not in ["", "mobile"]]
        if not parts:
            return "src/views/HomeView.vue", "src/views/HomeDetail.vue"

        last = parts[-1]
        last_lower = last.lower()
        is_list_segment = last_lower in ("list", "index", "items", "records")
        is_param = last.startswith(":")

        dir_parts = [p for p in parts if not p.startswith(":")]
        
        if not dir_parts:
            return "src/views/IndexView.vue", "src/views/IndexDetail.vue"
        
        content_parts = [
            p for p in dir_parts
            if p.lower() not in ("detail", "list", "index", "items", "records")
        ]
        title_content = "".join(p.title().replace("-", "") for p in content_parts) or "Index"
        title_dir = "".join(p.title().replace("-", "") for p in dir_parts) or "Index"

        if is_list_segment:
            list_name = title_dir + "List"
            detail_name = title_content + "Detail"
        elif is_param:
            list_name = None
            detail_name = title_content
        elif len(parts) == 1:
            list_name = title_dir + "View"
            detail_name = title_dir + "Detail"
        else:
            list_name = title_dir
            detail_name = title_dir + "Detail"

        list_path = f"src/views/{list_name}.vue" if list_name else None
        detail_path = f"src/views/{detail_name}.vue"

        return list_path, detail_path

    async def generate_page(
        self,
        view_path: str,
        page: PageDefinition | None,
        context: GenerationContext,
        session: any,
    ) -> GenerationResult:
        """为单个页面生成视图文件。"""
        try:
            page = page or self._create_default_page(view_path)
            view_name = view_path.replace("src/views/", "").replace(".vue", "")
            
            if self._has_detail_param(page.path):
                content = self._generate_list_view(page)
            else:
                content = self._generate_list_view(page)
            
            self._save_file(view_path, content, context.project_path)
            
            return GenerationResult(
                success=True,
                files_generated=[view_path],
                files_content={view_path: content},
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return GenerationResult(success=False, error=str(e))

    def _create_default_page(self, view_path: str) -> PageDefinition:
        """从视图路径创建默认页面定义。"""
        from ..analyzers.structure import PageDefinition
        view_name = view_path.replace("src/views/", "").replace(".vue", "")
        module = view_name.lower()
        path = f"/{module}"
        route_name = view_name.lower().replace("-", " ").replace("view", "").strip()
        
        return PageDefinition(
            path=path,
            route_name=route_name,
            component=view_name,
            module=module,
        )

    def _has_detail_param(self, path: str) -> bool:
        return ":id" in path or ":pk" in path or ":uuid" in path

    def _generate_list_view(self, page: PageDefinition) -> str:
        module = page.module
        # 规范化模块名
        normalized_module = normalize_module_name(module)
        normalized_type = normalize_type_name(module.title())
        page_title = page.route_name.replace("-", " ").title()
        composable_name = f"use{normalized_type}"
        store_name = f"use{normalized_type}Store"
        item_name = f"{normalized_type}Item"

        return f"""<script setup lang="ts">
import {{ ref, onMounted }} from 'vue'
import {{ storeToRefs }} from 'pinia'
import {{ ElMessage, ElMessageBox }} from 'element-plus'
import {{ {composable_name} }} from '@/composables/{composable_name}'
import {{ {store_name} }} from '@/stores/{normalized_module}'
import type {{ {item_name} }} from '@/types/{normalized_module}'

const store = {store_name}()
const {{ list, total, loading }} = storeToRefs(store)
const {{ loadList, handleDelete, handleCreate, handleUpdate }} = {composable_name}()

const searchForm = ref<Record<string, unknown>>({{
  keyword: '',
  page: 1,
  pageSize: 10,
}})

async function onSearch() {{
  searchForm.value.page = 1
  await loadList(searchForm.value)
}}

async function onReset() {{
  searchForm.value = {{ keyword: '', page: 1, pageSize: 10 }}
  await loadList(searchForm.value)
}}

async function onPageChange(page: number) {{
  searchForm.value.page = page
  await loadList(searchForm.value)
}}

async function onSizeChange(size: number) {{
  searchForm.value.pageSize = size
  searchForm.value.page = 1
  await loadList(searchForm.value)
}}

function onView(row: {item_name}) {{
  ElMessage.info(`查看: ${{row.id}}`)
}}

function onEdit(row: {item_name}) {{
  handleUpdate(row.id, row)
}}

async function onDelete(row: {item_name}) {{
  try {{
    await ElMessageBox.confirm('确定删除该数据吗？此操作不可撤销。', '删除确认', {{
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
    }})
    await handleDelete(row.id)
    ElMessage.success('删除成功')
    await loadList(searchForm.value)
  }} catch {{
    // user cancelled
  }}
}}

onMounted(() => {{
  onSearch()
}})
</script>

<template>
  <div class="{module}-list-page p-6">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span class="text-base font-medium">{page_title}列表</span>
          <el-button type="primary" @click="handleCreate">新增</el-button>
        </div>
      </template>

      <el-form :model="searchForm" inline class="mb-4" @submit.prevent="onSearch">
        <el-form-item label="关键词" class="mb-0">
          <el-input
            v-model="searchForm.keyword"
            placeholder="请输入关键词搜索"
            clearable
            class="w-64"
          />
        </el-form-item>
        <el-form-item class="mb-0">
          <el-button type="primary" @click="onSearch">搜索</el-button>
          <el-button @click="onReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column type="index" label="序号" width="60" />
        <slot />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{{ row }}">
            <el-button link type="primary" @click="onView(row)">查看</el-button>
            <el-button link type="primary" @click="onEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="mt-4 flex justify-end">
        <el-pagination
          v-model:current-page="searchForm.page"
          v-model:page-size="searchForm.pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="onPageChange"
          @size-change="onSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.{module}-list-page {{
  height: 100%;
}}
</style>
"""

    def _generate_detail_view(self, page: PageDefinition) -> str:
        module = page.module
        module_title = module.title().replace("-", "")
        page_title = page.route_name.replace("-", " ").title()
        item_name = f"{module_title}Item"
        composable_name = f"use{module_title}"
        store_name = f"use{module_title}Store"

        return f"""<script setup lang="ts">
import {{ ref, onMounted }} from 'vue'
import {{ useRoute, useRouter }} from 'vue-router'
import {{ ElMessage }} from 'element-plus'
import {{ {composable_name} }} from '@/composables/{composable_name}'
import {{ {store_name} }} from '@/stores/{module}'
import type {{ {item_name} }} from '@/types/{module}'

const route = useRoute()
const router = useRouter()
const store = {store_name}()
const {{ loadDetail }} = {composable_name}()

const loading = ref(false)
const formData = ref<Record<string, unknown>>({{}})

const id = route.params.id as string

async function fetchData() {{
  loading.value = true
  try {{
    await loadDetail(id)
    formData.value = {{ ...(store.currentItem as any) }}
  }} catch (e) {{
    ElMessage.error('加载详情失败')
  }} finally {{
    loading.value = false
  }}
}}

function onBack() {{
  router.back()
}}

onMounted(() => {{
  fetchData()
}})
</script>

<template>
  <div class="{module}-detail-page p-6">
    <el-card v-loading="loading" shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span class="text-base font-medium">{page_title}详情</span>
          <el-button @click="onBack">返回</el-button>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="ID">
          {{ '{{' }} formData.id {{ '}}' }}
        </el-descriptions-item>
        <slot name="detail-items" />
      </el-descriptions>
    </el-card>
  </div>
</template>

<style scoped>
.{module}-detail-page {{
  height: 100%;
}}
</style>
"""

    def _generate_not_found(self) -> str:
        return """<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome() {
  router.push('/')
}
</script>

<template>
  <div class="not-found-page flex items-center justify-center h-full">
    <el-result
      icon="error"
      title="404"
      sub-title="抱歉，您访问的页面不存在"
    >
      <template #extra>
        <el-button type="primary" @click="goHome">返回首页</el-button>
      </template>
    </el-result>
  </div>
</template>

<style scoped>
.not-found-page {
  height: 100%;
}
</style>
"""
