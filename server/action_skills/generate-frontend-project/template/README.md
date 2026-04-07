# Vue Admin Starter

这是一个给 AI 大模型生成前端业务页面时使用的底座项目。

目标很简单：

- 保留统一布局、主题、登录、路由、请求封装
- 新项目只增加业务页面、接口模块、菜单配置
- mock 数据和真实接口可以快速切换

## 技术栈

- Vue 3.5+
- Vite 6
- TypeScript
- Pinia
- pinia-plugin-persistedstate
- Vue Router 4
- Tailwind CSS 4
- Element Plus
- @vueuse/core

## 启动命令

```bash
npm install
npm run dev
```

常用命令：

```bash
npm run typecheck
npm run lint
npm run build
```

## 目录说明

```text
src/
├─ api/
│  ├─ http.ts                统一请求实例、请求拦截、响应拦截
│  └─ modules/               业务接口模块
├─ assets/                   logo、favicon、图片资源
├─ components/               通用组件
├─ constants/                常量
├─ layouts/                  全局布局
├─ mock/                     mock 模拟接口
├─ router/                   路由配置
├─ stores/                   Pinia 状态
├─ views/                    页面文件
├─ App.vue
├─ main.ts
└─ style.css
```

## 业务页面应该放哪里

业务页面统一放在 `src/views` 下。

推荐方式：

```text
src/views/
└─ order/
   ├─ OrderListView.vue
   ├─ OrderDetailView.vue
   └─ OrderEditView.vue
```

如果页面较多，建议按业务模块建子目录，不要把所有页面直接堆在 `views` 根目录。

## 路由怎么加

路由统一写在 `src/router/index.ts`。

现在模板里的页面路由就是在这里配置的。

新增一个业务页面时，直接在 `children` 里增加一项，例如：

```ts
{
  path: 'order/list',
  name: 'order-list',
  component: () => import('@/views/order/OrderListView.vue'),
  meta: {
    title: '订单列表',
    description: '订单管理列表',
    requiresAuth: true,
  },
}
```

说明：

- `path`：页面地址
- `name`：路由唯一名称
- `component`：页面文件路径
- `meta.title`：浏览器标题和页面标题使用
- `meta.requiresAuth`：是否需要登录

## 菜单怎么加

左侧菜单现在写在 `src/layouts/AppLayout.vue` 里的 `navigationGroups`。

新增菜单时，需要同步增加一条菜单配置，例如：

```ts
{
  title: '订单模块',
  items: [
    {
      icon: List,
      label: '订单列表',
      path: '/order/list',
    },
  ],
}
```

注意：

- 菜单 `path` 必须和路由里的 `path` 对应
- 先加路由，再加菜单
- 如果只加路由不加菜单，页面可以访问，但左侧不会显示入口

## 接口写哪里

业务接口统一放在 `src/api/modules` 下。

每个业务模块单独一个文件，推荐这样组织：

```text
src/api/modules/
├─ auth.ts
├─ dashboard.ts
├─ module.ts
└─ order.ts
```

例如新建 `src/api/modules/order.ts`：

```ts
import { get, post } from '@/api/http'

export interface OrderRecord {
  id: number
  orderNo: string
  status: string
}

export const fetchOrderListApi = () => get<OrderRecord[]>('/orders')

export const createOrderApi = (payload: Record<string, unknown>) =>
  post<OrderRecord>('/orders', payload)
```

不要在页面里直接写 axios，统一走 `src/api/http.ts`。

这样可以复用：

- token 注入
- 401 跳登录
- 统一错误提示
- mock / 真实接口切换

## 模拟数据写哪里

mock 数据统一写在 `src/mock/server.ts`。

现在模板已经内置了一个 axios adapter，会拦截请求并返回模拟数据。

例如新增订单 mock：

```ts
if (url === '/orders' && method === 'get') {
  return buildResponse(config, {
    code: SUCCESS_CODE,
    data: [
      { id: 1, orderNo: 'SO20260331001', status: 'pending' },
    ],
    message: '获取成功',
  })
}
```

## 真实接口和 mock 怎么切换

统一在 `src/api/http.ts` 里切换：

```ts
adapter: import.meta.env.VITE_USE_MOCK === 'false' ? undefined : mockAdapter
```

规则：

- `VITE_USE_MOCK !== 'false'`：走 mock
- `VITE_USE_MOCK === 'false'`：走真实接口

真实接口基础地址：

```ts
baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api'
```

推荐新增环境变量文件：

```bash
.env.development
.env.production
```

例如：

```env
VITE_USE_MOCK=false
VITE_API_BASE_URL=https://api.example.com
```

## 页面开发推荐流程

给 AI 生成业务模块时，按下面步骤做：

1. 在 `src/views/业务模块` 下创建页面
2. 在 `src/api/modules` 下创建接口文件
3. 在 `src/mock/server.ts` 下补 mock 数据
4. 在 `src/router/index.ts` 下增加路由
5. 在 `src/layouts/AppLayout.vue` 下增加菜单
6. 如果页面有状态，再补 `src/stores` 下的 store

## Store 写哪里

全局或模块状态统一放在 `src/stores` 下。

例如：

```text
src/stores/
├─ app.ts
├─ auth.ts
└─ order.ts
```

当前模板里：

- `app.ts`：主题、侧边栏状态
- `auth.ts`：登录态、用户信息

项目已接入官方 `pinia-plugin-persistedstate`，可直接使用：

```ts
persist: {
  key: 'order-store',
  pick: ['filters', 'selectedId'],
}
```

## 页面样式怎么复用

优先复用现有模板页：

- `src/views/ListTemplateView.vue`：列表页模板
- `src/views/FormTemplateView.vue`：表单页模板

建议做法：

- 列表页：复制列表模板，替换筛选项、列配置、接口
- 表单页：复制表单模板，替换字段、校验规则、提交逻辑

## AI 生成页面时的建议约束

建议直接把下面要求给大模型：

```text
1. 页面使用 Vue 3 <script setup> + TypeScript
2. 页面文件放到 src/views/业务模块 下
3. 接口统一写到 src/api/modules/业务模块.ts
4. 不要在页面里直接写 axios，统一调用 src/api/http.ts 导出的 get/post
5. 如果需要模拟数据，把 mock 写到 src/mock/server.ts
6. 新页面要同步补充 src/router/index.ts 路由
7. 新菜单要同步补充 src/layouts/AppLayout.vue 的 navigationGroups
8. 优先复用 Element Plus 和现有模板布局
```

## 当前模板已包含

- 登录页
- 首页
- 列表模板页
- 表单模板页
- 404 页面
- 路由鉴权
- 主题切换
- 左侧导航
- 请求拦截
- mock 模拟接口
- Pinia 持久化

## 一句话使用方式

这个模板不是从零开发业务，而是：

**先复制模板页结构，再补页面、接口、mock、路由、菜单，最后替换成真实业务数据。**
