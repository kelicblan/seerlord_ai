# 系统开发综合指导手册

## 第一部分：产品需求文档 (PRD & UI)

### 1. 全局交互规范
- **异常处理机制**：  
  - 断网时显示"网络异常，请检查连接"弹窗（持续3秒）  
  - API报错时展示"系统异常，请稍后重试"提示，包含错误代码（如：API_001）  
- **全局样式规范**：  
  - 主色调：#2C3E50（深蓝）  
  - 弹窗背景色：rgba(0,0,0,0.5)  
  - 按钮圆角：8px  
  - 字体：Roboto, 14px  

### 2. 详细功能逻辑
#### 流程图 (Flowchart)
```mermaid
graph TD
    A[查看附件] -->|点击审批按钮| B[申请下载审批]
    B -->|确认操作| C[推送审批任务]
    C --> D{审批状态}
    D -->|通过| E[显示下载按钮]
    D -->|拒绝| F[通知申请人]
    F --> G[记录操作日志]
    C --> H[记录操作日志]```

#### 字段定义
| 字段名称       | 类型        | 长度 | 必填 | 校验规则                  |
|----------------|-------------|------|------|---------------------------|
| 文件名         | varchar     | 255  | 是   | 中文/英文/数字/下划线     |
| 用户IP         | varchar     | 15   | 是   | IPv4格式校验              |
| 审批人ID       | bigint      | -    | 是   | 不存在时自动创建审批人    |
| 操作时间       | datetime    | -    | 是   | 自动记录UTC时间          |

#### UI原型/高保真图
- 原型链接：[Figma链接](https://figma.com/design/attachment-access-control)  
- 交互说明：  
  - 点击"申请下载审批"按钮时，触发弹窗确认  
  - 审批状态变化时，实时刷新附件区域  
  - 所有操作需记录日志并支持审计追溯

## 第二部分：详细架构与技术方案 (Technical Specification)

### 1. 技术栈详细清单
- **后端**：Spring Boot 3.2 + MyBatis Plus  
- **前端**：React 18 + TypeScript  
- **Python**：用于审批流程自动化处理（Python 3.10+）  
- **中间件**：  
  - Redis（缓存操作日志）  
  - RabbitMQ（审批消息队列）  
  - Elasticsearch（审计日志检索）  

### 2. 数据库设计 (Database Design)
#### ER图 (Entity-Relationship Diagram)
```mermaid
erDiagram
    user ||--o{ approval_request : "申请记录"
    user ||--o{ file_access_log : "访问日志"
    approval_request }|--o{ approval_result : "审批结果"
    approval_result }|--o{ approval_record : "审批记录"```

#### 数据字典
**文件访问日志表（file_access_log）**
| 字段名         | 类型        | 索引 | 说明           |
|----------------|-------------|------|----------------|
| id             | BIGINT PK   | 是   | 主键           |
| user_id        | BIGINT      | 是   | 关联用户表     |
| file_name      | VARCHAR(255)| 是   | 文件名         |
| access_time    | DATETIME    | 是   | 访问时间       |
| approval_status| TINYINT     | 是   | 0:待审批 1:通过 2:拒绝 |

**审批请求表（approval_request）**
| 字段名         | 类型        | 索引 | 说明           |
|----------------|-------------|------|----------------|
| id             | BIGINT PK   | 是   | 主键           |
| file_id        | BIGINT      | 是   | 关联文件表     |
| user_id        | BIGINT      | 是   | 关联用户表     |
| request_time   | DATETIME    | 是   | 申请时间       |
| status         | TINYINT     | 是   | 0:待审批 1:通过 2:拒绝 |

### 3. API 接口规范
- **协议**：HTTPS + JSON  
- **统一响应结构**：
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "approvalId": "APR-20251222-001"
  }
}
```
- **鉴权机制**：JWT + OAuth2（客户端模式）  
  - Token有效期：24小时  
  - 刷新Token：7天  
  - 接口权限校验：基于Spring Security的RBAC模型  

### 4. 工程结构与规范
**代码目录结构**
```
src/
├── main/
│   ├── java/                 # 后端代码
│   │   ├── com.example.core  # 核心业务逻辑
│   │   └── com.example.api   # 接口定义
│   └── resources/            # 配置文件
│       └── application.yml
├── test/                     # 单元测试
└── public/                   # 前端资源
```

**Git分支管理策略**
- 主分支：`main`（稳定版本）
- 开发分支：`dev`（集成开发）
- 功能分支：`feature/attachment-access`（当前项目）
- 版本分支：`release/v1.0`（发布前准备）

## 第三部分：WBS与进度执行 (Execution Plan)

### 1. WBS 工时估算表
| 模块               | 子任务                   | 前置任务         | 后端负责人 | 前端负责人 | 预估工时(h) | 开始时间 | 截止时间 | 风险备注         |
|--------------------|--------------------------|------------------|------------|------------|-------------|----------|----------|------------------|
| 审批流程开发       | 审批状态管理             | -                | 张伟       | 李娜       | 8           | 2025-01-05 | 2025-01-08 | 需同步日志模块   |
|                    | 审批消息推送             | 审批状态管理     | 王强       | -          | 6           | 2025-01-08 | 2025-01-10 | 需确认MQ配置     |
|                    | 审批结果通知             | 审批消息推送     | 李娜       | 王芳       | 4           | 2025-01-10 | 2025-01-12 | 需测试通知渠道   |
| UI交互开发         | 按钮状态控制             | -                | -          | 王芳       | 6           | 2025-01-05 | 2025-01-08 | 需配合后端接口   |
|                    | 弹窗交互开发             | 按钮状态控制     | -          | 李娜       | 4           | 2025-01-08 | 2025-01-10 | 需测试动画效果   |
| 日志模块开发       | 操作日志记录             | -                | 张伟       | -          | 8           | 2025-01-05 | 2025-01-08 | 需设计存储方案   |
|                    | 日志检索功能             | 操作日志记录     | 王强       | -          | 6           | 2025-01-08 | 2025-01-10 | 需对接ES         |

### 2. 项目进度计划 (Gantt Chart)
```mermaid
gantt
    title 项目进度计划
    dateFormat  YYYY-MM-DD
    axisFormat  %m/%d
    excludes    weekends

    section 需求阶段
    需求分析            :a1, 2025-01-01, 5d
    原型/交互确认        :a2, after a1, 5d

    section 开发阶段
    后端审批模块开发     :b1, after a2, 10d
    前端交互开发         :b2, after a2, 10d
    联调                :milestone, m1, after b1, 1d

    section 测试与上线
    提测                :milestone, m2, after m1, 1d
    测试修复            :c1, after m2, 5d
    上线                :milestone, m3, after c1, 1d```