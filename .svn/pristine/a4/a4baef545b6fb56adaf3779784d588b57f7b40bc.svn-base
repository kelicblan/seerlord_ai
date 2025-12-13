#!/bin/bash

# 退出脚本如果任何命令失败
set -e

echo "Starting SeerLord AI Kernel (Production Mode)..."

# 1. 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "[ERROR] Virtual environment (.venv) not found!"
    echo "Please run the following commands first:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# 2. 设置环境变量
export PYTHONPATH=$(pwd)
# 可以在这里设置其他生产环境变量，或者依赖 .env 文件

# 3. 启动服务
# 使用 uvicorn 启动，推荐在生产环境中使用 gunicorn + uvicorn worker
# 这里使用简单的 uvicorn 启动方式，适合轻量级部署
# 如果需要高性能，可以使用:
# .venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

echo "Launching Uvicorn..."
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

