# 资产管理系统 (AMS) 前端代码生成文档

## 一、技术栈要求

| 技术 | 版本要求 |
|------|----------|
| Vue | 3.5+ |
| Vite | 6.x |
| TypeScript | 5.x |
| Element Plus | 2.x |
| Tailwind CSS | 4.x |
| Pinia | 2.x |
| Vue Router | 4.x |
| @vueuse/core | 最新版 |

## 二、业务模块

| 模块名称 | 模块标识 | 功能描述 |
|----------|----------|----------|
| 认证模块 | auth | 用户登录、注册、登出 |
| 资产模块 | asset | 资产管理（增删改查） |
| 库存模块 | inventory | 库存管理 |
| 用户模块 | user | 用户管理 |
| 系统模块 | system | 系统配置 |

## 三、功能需求覆盖矩阵

| 需求ID | 需求名称 | 所属模块 | 页面路径 | 路由名称 | API模块 | LLD来源 |
|--------|----------|----------|----------|----------|---------|---------|
| REQ-FUN-001 | 资产列表查询 | asset | /asset/list | asset-list | asset | 5.2.1 |
| REQ-FUN-002 | 资产详情查看 | asset | /asset/detail/:id | asset-detail | asset | 5.2.2 |
| REQ-FUN-003 | 资产新增 | asset | /asset/create | asset-create | asset | 5.2.3 |
| REQ-FUN-004 | 资产编辑 | asset | /asset/edit/:id | asset-edit | asset | 5.2.4 |
| REQ-FUN-005 | 资产删除 | asset | /asset/list | asset-list | asset | 5.2.5 |
| REQ-FUN-006 | 库存列表查询 | inventory | /inventory/list | inventory-list | inventory | 6.2.1 |
| REQ-FUN-007 | 库存任务详情 | inventory | /inventory/task/detail/:id | inventory-task-detail | inventory | 6.2.2 |
| REQ-FUN-008 | 用户登录 | auth | /login | login | auth | 4.2.1 |
| REQ-FUN-009 | 用户登出 | auth | - | - | auth | 4.2.2 |
| REQ-FUN-010 | 用户列表 | user | /user/list | user-list | user | 7.2.1 |

## 四、页面列表

### 4.1 认证模块页面

| 页面路径 | 组件名称 | 路由名称 | 所需组件 |
|----------|----------|----------|----------|
| /login | Login.vue | login | LoginForm.vue |

### 4.2 资产模块页面

| 页面路径 | 组件名称 | 路由名称 | 所需组件 |
|----------|----------|----------|----------|
| /asset/list | AssetList.vue | asset-list | AssetTable.vue, AssetFilter.vue |
| /asset/detail/:id | AssetDetail.vue | asset-detail | AssetInfo.vue |
| /asset/create | AssetCreate.vue | asset-create | AssetForm.vue |
| /asset/edit/:id | AssetEdit.vue | asset-edit | AssetForm.vue |

### 4.3 库存模块页面

| 页面路径 | 组件名称 | 路由名称 | 所需组件 |
|----------|----------|----------|----------|
| /inventory/list | InventoryList.vue | inventory-list | InventoryTable.vue |
| /inventory/task/detail/:id | InventoryTaskDetail.vue | inventory-task-detail | TaskInfo.vue |

### 4.4 用户模块页面

| 页面路径 | 组件名称 | 路由名称 | 所需组件 |
|----------|----------|----------|----------|
| /user/list | UserList.vue | user-list | UserTable.vue |

## 五、API 模块

### 5.1 auth 模块

| 接口名称 | 接口路径 | 方法 |
|----------|----------|------|
| 登录 | /api/auth/login | POST |
| 登出 | /api/auth/logout | POST |
| 获取用户信息 | /api/auth/userinfo | GET |

### 5.2 asset 模块

| 接口名称 | 接口路径 | 方法 |
|----------|----------|------|
| 资产列表 | /api/asset/list | GET |
| 资产详情 | /api/asset/detail/:id | GET |
| 新增资产 | /api/asset/create | POST |
| 编辑资产 | /api/asset/update/:id | PUT |
| 删除资产 | /api/asset/delete/:id | DELETE |

### 5.3 inventory 模块

| 接口名称 | 接口路径 | 方法 |
|----------|----------|------|
| 库存列表 | /api/inventory/list | GET |
| 任务详情 | /api/inventory/task/detail/:id | GET |

### 5.4 user 模块

| 接口名称 | 接口路径 | 方法 |
|----------|----------|------|
| 用户列表 | /api/user/list | GET |
| 用户详情 | /api/user/detail/:id | GET |
| 新增用户 | /api/user/create | POST |

## 六、Store 定义

| Store名称 | 所属模块 | 状态描述 |
|-----------|----------|----------|
| useAuthStore | auth | token, userInfo, login, logout |
| useAssetStore | asset | list, total, loading, fetchList, create, update, delete |
| useInventoryStore | inventory | list, total, loading, fetchList |
| useUserStore | user | list, total, loading, fetchList, create |
