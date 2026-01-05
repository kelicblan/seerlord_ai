# SeerLord AI 安装部署指南

本指南将帮助您完成 SeerLord AI 的安装与部署。本项目支持 Docker 一键部署（推荐）和手动分步部署。

## 1. 环境要求

*   **操作系统**: Linux, Windows, macOS
*   **Docker**: 20.10+ (如果使用 Docker 部署)
*   **Python**: 3.10+ (如果手动部署后端)
*   **Node.js**: 18+ (如果手动部署前端)
*   **PostgreSQL**: 16+

## 2. 快速启动 (Docker 部署) - 推荐

这是最简单的部署方式，会自动构建前端、后端并启动数据库。

### 步骤

1.  **克隆项目**
    ```bash
    git clone https://github.com/your-repo/seerlord_ai.git
    cd seerlord_ai
    ```

2.  **配置环境变量**
    复制示例配置文件：
    ```bash
    cp .env.example .env
    ```
    编辑 `.env` 文件，填入您的 API Key（如 OpenAI API Key 等）。数据库配置默认即可。

3.  **启动服务**
    ```bash
    docker-compose up -d --build
    ```

4.  **访问应用**
    等待几分钟构建完成后，访问浏览器：
    *   **地址**: `http://localhost:8000`
    *   **说明**: 后端服务会自动托管前端页面，无需单独配置 Nginx。

## 3. 手动部署指南

如果您用于开发或需要精细控制，可以手动部署。

### 3.1 数据库准备

1.  安装并启动 PostgreSQL。
2.  创建一个空的数据库（例如 `seerlord`）。
    ```sql
    CREATE DATABASE seerlord;
    ```

### 3.2 后端部署 (Python)

1.  **创建虚拟环境**
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/Mac
    source .venv/bin/activate
    ```

2.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

3.  **配置环境**
    复制 `.env.example` 为 `.env`，并修改数据库连接信息：
    ```ini
    DATABASE_URL=postgresql://user:password@localhost:5432/seerlord
    ```

4.  **数据库初始化**
    项目启动时会自动检查并创建表结构。如果您需要手动执行 SQL 初始化，可以使用项目根目录下的 `db_schema.sql` 文件。
    
    或者运行 Python 脚本进行初始化（如果表不存在）：
    ```bash
    python scripts/init_db.py
    ```
    > **注意**：该脚本还会自动创建一个默认的管理员账户。

5.  **启动后端**
    ```bash
    uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    后端 API 将运行在 `http://localhost:8000`。

### 3.3 前端部署 (Vue3)

1.  **进入前端目录**
    ```bash
    cd admin
    ```

2.  **安装依赖**
    ```bash
    npm install
    ```

3.  **开发模式运行**
    ```bash
    npm run dev
    ```
    前端将运行在 `http://localhost:5173`。开发模式下需要确保 `.env` 中的 API 地址指向后端。

4.  **生产环境构建**
    如果您想将前端集成到后端服务中：
    ```bash
    npm run build
    ```
    构建完成后，将 `admin/dist` 目录下的所有文件复制到 `server/static/` 目录下。重启后端服务后，即可通过 `http://localhost:8000` 访问前端。

## 4. 默认管理员账户

数据库初始化完成后（无论是通过 Docker 还是 `init_db.py`），系统会自动创建一个默认管理员账户：

*   **用户名**: `seerlord`
*   **密码**: `12345678`

## 5. 数据库初始化说明

本项目采用 SQLAlchemy ORM 管理数据库结构。

*   **自动初始化**: 每次启动应用 (`server/main.py`) 或运行 `scripts/init_db.py` 时，系统会自动检测并创建缺失的表。
*   **手动 SQL**: 如果您处于无法运行 Python 的环境，或者需要审计 SQL 结构，可以使用根目录下的 `db_schema.sql` 文件直接在数据库中执行。
    ```bash
    psql -U user -d seerlord -f db_schema.sql
    ```

## 6. 常见问题

**Q: 启动时报错 "FATAL: password authentication failed for user"**
A: 请检查 `.env` 文件中的 `DATABASE_URL` 是否与您本地或 Docker 的数据库密码一致。

**Q: 页面显示 404 Not Found**
A: 如果是访问 `http://localhost:8000` 报 404，说明前端静态文件没有正确加载。请确保您已经运行了 `npm run build` 并将产物复制到了 `server/static`，或者使用 Docker 部署（会自动处理此步骤）。
