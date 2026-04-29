@echo off
chcp 65001 >nul
echo ========================================
echo   A股量化分析系统 - 安装脚本
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.12+
    pause
    exit /b 1
)

echo [1/3] 创建虚拟环境...
if not exist .venv (
    python -m venv .venv
)

echo [2/3] 激活虚拟环境并安装依赖...
call .venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo [3/3] 创建输出目录...
if not exist outputs mkdir outputs
if not exist outputs\reports mkdir outputs\reports
if not exist outputs\charts mkdir outputs\charts
if not exist outputs\data mkdir outputs\data
if not exist outputs\json mkdir outputs\json

echo.
echo ========================================
echo   安装完成！
echo   运行 start.bat 启动应用
echo ========================================
pause