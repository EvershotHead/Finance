@echo off
chcp 65001 >nul
echo ========================================
echo   A股量化分析系统 - 启动中...
echo ========================================

if not exist .venv (
    echo [提示] 未找到虚拟环境，请先运行 setup.bat
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python -m streamlit run app.py
