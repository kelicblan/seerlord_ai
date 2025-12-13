# SeerLord AI

> **SeerLord AI**：基于微内核架构与 LangGraph 的下一代模块化 AI 智能体编排平台，原生支持 MCP 协议与人机协同（Human-in-the-loop），让复杂 Agent 开发更稳定、更灵活。

SeerLord AI 是一个基于**微内核 + 插件化架构**构建的模块化 AI 平台。它利用 LangGraph 进行强大的智能体（Agent）编排，支持灵活的插件扩展，旨在为开发者提供一个高效、可扩展的 AI 应用开发框架。

## 🌟 项目亮点

- **微内核架构 (Micro-Kernel)**: 核心系统轻量稳定，负责生命周期管理、上下文共享和资源调度。
- **插件化系统 (Plugin System)**: 所有的业务能力（如新闻播报、教程生成、金融分析等）均通过插件实现，即插即用。
- **智能体编排 (LangGraph)**: 利用 LangGraph 构建复杂的有状态多智能体工作流。
- **MCP 支持**: 集成 Model Context Protocol (MCP)，实现标准化的上下文和工具交互。
- **高性能后端**: 基于 FastAPI 构建的异步后端，支持 SSE 流式响应。

## 🛠️ 技术栈

- **语言**: Python 3.11+
- **框架**: FastAPI, LangChain, LangGraph
- **数据库**: PostgreSQL (AsyncPG)
- **工具库**: Pydantic, Loguru, SSE-Starlette

## 📂 目录结构

```
seerlord_ai/
├── server/
│   ├── core/           # 核心配置与 LLM 封装
│   ├── kernel/         # 微内核实现 (注册表, MCP 管理, 记忆管理)
│   ├── plugins/        # 插件目录 (包含各类 Agent 实现)
│   └── main.py         # 应用入口
├── mcp_services/       # MCP 服务实现
├── scripts/            # 实用脚本
└── pyproject.toml      # 项目依赖配置
```

## 🚀 快速开始

### 前置要求

- Python 3.11 或更高版本
- PostgreSQL 数据库

### 安装依赖

建议使用 Poetry 或 pip 进行安装。

```bash
# 使用 pip 安装依赖
pip install -r requirements.txt
```

### 配置环境

复制环境变量示例文件并修改配置：

```bash
cp .env.example .env
# 编辑 .env 文件，配置 OpenAI API Key 和数据库连接信息
```

### 启动服务

```bash
# 启动后端服务
python server/main.py
```

## 📄 开源协议

本项目采用 [MIT 许可证](LICENSE) 开源。

这意味着您可以自由地：
- ✅ 商业使用
- ✅ 修改代码
- ✅ 分发副本
- ✅ 私有使用

只需在副本中包含原始许可证和版权声明即可。
