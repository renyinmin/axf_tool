@echo off
chcp 65001 >nul
echo ========================================
echo Modbus AXF 工具启动器
echo ========================================
echo.

REM 显示当前目录
echo 当前目录: %CD%
echo.

REM 检查虚拟环境是否存在
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 虚拟环境不存在
    echo 请在modbus_axf_tool目录下运行此脚本
    echo.
    echo 如果虚拟环境不存在，请先创建：
    echo   python -m venv .venv
    echo.
    echo 然后安装依赖：
    echo   .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo [OK] 虚拟环境已找到
echo.

REM 检查main.py是否存在
if not exist "main.py" (
    echo [错误] main.py文件不存在
    echo 请确保在modbus_axf_tool目录下运行此脚本
    echo.
    pause
    exit /b 1
)

echo [OK] main.py已找到
echo.

REM 检查requirements.txt
if exist "requirements.txt" (
    echo [OK] requirements.txt已找到
    echo.
)

echo 启动程序...
echo ========================================
echo.

REM 使用虚拟环境的Python运行
.venv\Scripts\python.exe main.py %*

REM 如果程序出错，暂停以查看错误信息
if errorlevel 1 (
    echo.
    echo ========================================
    echo 程序运行出错，错误代码: %errorlevel%
    echo ========================================
    echo.
    pause
)
