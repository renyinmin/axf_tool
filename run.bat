@echo off
chcp 65001 >nul
echo 启动 Modbus AXF 工具...
echo.

REM 检查虚拟环境是否存在
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 虚拟环境不存在，请先创建虚拟环境
    echo 运行: python -m venv .venv
    echo 然后运行: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

REM 使用虚拟环境的Python运行
.venv\Scripts\python.exe main.py %*
