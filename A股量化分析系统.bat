@echo off
chcp 65001 >nul
title A股量化分析系统
color 0A

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║        A股量化分析系统 一键启动          ║
echo  ╚══════════════════════════════════════════╝
echo.

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 步骤1：检查/创建虚拟环境
if exist ".venv\Scripts\python.exe" (
    echo [信息] 找到内置 Python 环境
    set PYTHON=.venv\Scripts\python.exe
) else (
    echo [步骤 1/3] 未找到内置环境，正在创建...
    
    :: 查找系统 Python
    where python >nul 2>&1
    if errorlevel 1 (
        echo [错误] 未找到 Python！
        echo 请先安装 Python 3.10+：https://www.python.org/downloads/
        echo 安装时请勾选 "Add Python to PATH"
        pause
        exit /b 1
    )
    
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [信息] %%i
    
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo [完成] 虚拟环境已创建
    set PYTHON=.venv\Scripts\python.exe
)

:: 步骤2：检查/安装依赖
%PYTHON% -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [步骤 2/3] 正在安装依赖包（首次约需3-5分钟）...
    echo           请耐心等待，不要关闭窗口...
    echo.
    %PYTHON% -m pip install --upgrade pip -q
    %PYTHON% -m pip install -r requirements.txt -q
    if errorlevel 1 (
        echo [警告] 部分依赖安装失败，尝试重新安装...
        %PYTHON% -m pip install -r requirements.txt
    )
    echo [完成] 依赖包安装完成
) else (
    echo [信息] 依赖包已就绪
)

:: 创建输出目录
if not exist "outputs" mkdir "outputs"
if not exist "outputs\reports" mkdir "outputs\reports"
if not exist "outputs\charts" mkdir "outputs\charts"
if not exist "outputs\data" mkdir "outputs\data"
if not exist "outputs\json" mkdir "outputs\json"
if not exist "data_cache" mkdir "data_cache"

:: 步骤3：启动应用
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║  正在启动，浏览器将自动打开             ║
echo  ║  http://localhost:8501                   ║
echo  ║  关闭此窗口将停止应用                    ║
echo  ╚══════════════════════════════════════════╝
echo.

%PYTHON% -m streamlit run app.py --server.headless false --browser.gatherUsageStats false

echo.
echo [信息] 应用已关闭
pause