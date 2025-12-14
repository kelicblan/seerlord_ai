@echo off
echo Starting SeerLord AI Kernel...

:: 检查 .venv 是否存在
if not exist ".venv" (
    echo [ERROR] Virtual environment not found!
    echo Please run 'python -m venv .venv' and 'pip install -r requirements.txt' first.
    pause
    exit /b 1
)

:: 设置 PYTHONPATH 确保可以导入 app 模块
set PYTHONPATH=%CD%

:: 启动 Uvicorn 服务
:: 使用 --host 0.0.0.0 允许外部访问
:: 使用 --workers 4 开启多进程模式（生产环境建议）
:: 在 Windows 上，workers 可能有限制，这里使用 1 个 worker 但保留配置供参考
.venv\Scripts\python -m server.main

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Server failed to start!
    pause
)
