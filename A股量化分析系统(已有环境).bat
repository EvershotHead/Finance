@echo off
title A股量化分析系统（已有环境）

:: 切换到脚本所在目录
cd /d "%~dp0"

echo.
echo  ============================================
echo    A 股量化分析系统 - 已有环境启动模式
echo  ============================================
echo.

:: 1) 选择 Python：优先 .venv，其次系统 python
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
    echo [信息] 使用项目虚拟环境 .venv
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [错误] 未找到 Python，且项目内不存在 .venv 环境。
        echo        请先安装 Python 或运行带安装功能的「A股量化分析系统.bat」。
        echo.
        pause
        exit /b 1
    )
    set "PYTHON=python"
    echo [信息] 使用系统 Python
)

for /f "tokens=*" %%i in ('%PYTHON% --version 2^>^&1') do echo [信息] %%i

:: 2) 检查关键依赖（一次性列出所有缺失项）
echo [信息] 正在检查依赖 ...
%PYTHON% -c "import importlib.util,sys;mods=['streamlit','akshare','pandas','numpy','plotly','loguru','pydantic','statsmodels','arch','sklearn','jinja2','seaborn','matplotlib','markdown'];miss=[m for m in mods if importlib.util.find_spec(m) is None];print('MISSING:'+','.join(miss)) if miss else print('OK')"
%PYTHON% -c "import importlib.util,sys;mods=['streamlit','akshare','pandas','numpy','plotly','loguru','pydantic','statsmodels','arch','sklearn','jinja2','seaborn','matplotlib','markdown'];miss=[m for m in mods if importlib.util.find_spec(m) is None];sys.exit(1 if miss else 0)" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [错误] 上方列出的依赖缺失，无法启动。
    echo 请执行下面任一方式安装：
    echo   1）在本窗口运行：  %PYTHON% -m pip install -r requirements.txt
    echo   2）改用「A股量化分析系统.bat」（首次自动安装到 .venv）
    echo.
    pause
    exit /b 1
)
echo [信息] 依赖检查通过

:: 3) 创建必要的输出目录（首次运行用）
if not exist "outputs"          mkdir "outputs"
if not exist "outputs\reports"  mkdir "outputs\reports"
if not exist "outputs\charts"   mkdir "outputs\charts"
if not exist "outputs\data"     mkdir "outputs\data"
if not exist "outputs\json"     mkdir "outputs\json"
if not exist "data_cache"       mkdir "data_cache"

:: 4) 启动 Streamlit（自动打开浏览器）
echo.
echo  ============================================
echo    正在启动，浏览器将自动打开
echo    http://localhost:8501
echo    关闭此窗口将停止应用
echo  ============================================
echo.

%PYTHON% -m streamlit run app.py --server.headless false --browser.gatherUsageStats false
set EXITCODE=%ERRORLEVEL%

echo.
if not "%EXITCODE%"=="0" (
    echo [警告] Streamlit 异常退出，错误码 %EXITCODE%
) else (
    echo [信息] 应用已正常关闭
)
pause
