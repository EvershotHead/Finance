#!/bin/bash
# =============================================
#   A股量化分析系统 - Linux 一键启动
#   用法: chmod +x start_linux.sh && ./start_linux.sh
# =============================================

set -e

# 切换到脚本所在目录
cd "$(dirname "$0")"

echo ""
echo "  ========================================"
echo "  |      A股量化分析系统 一键启动         |"
echo "  ========================================"
echo ""

# 检查 Python
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "[错误] 未找到 Python！"
    echo "请安装 Python 3.10+:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  CentOS/RHEL:   sudo yum install python3"
    echo ""
    exit 1
fi

# 检查 Python 版本
PY_VERSION=$($PYTHON_CMD --version 2>&1)
echo "[信息] Python: $PY_VERSION"

# 步骤1：检查/创建虚拟环境
if [ -f ".venv/bin/python" ]; then
    echo "[信息] 找到内置 Python 环境"
    PYTHON=".venv/bin/python"
else
    echo "[步骤 1/3] 未找到内置环境，正在创建..."
    $PYTHON_CMD -m venv .venv
    if [ $? -ne 0 ]; then
        echo "[错误] 创建虚拟环境失败"
        echo "请安装 python3-venv: sudo apt install python3-venv"
        exit 1
    fi
    echo "[完成] 虚拟环境已创建"
    PYTHON=".venv/bin/python"
fi

# 步骤2：检查/安装依赖
$PYTHON -c "import streamlit" &> /dev/null
if [ $? -ne 0 ]; then
    echo ""
    echo "[步骤 2/3] 正在安装依赖包（首次约需3-5分钟）..."
    echo "           请耐心等待..."
    echo ""
    $PYTHON -m pip install --upgrade pip -q
    $PYTHON -m pip install -r requirements.txt -q
    if [ $? -ne 0 ]; then
        echo "[警告] 部分依赖安装失败，尝试重新安装..."
        $PYTHON -m pip install -r requirements.txt
    fi
    echo "[完成] 依赖包安装完成"
else
    echo "[信息] 依赖包已就绪"
fi

# 创建输出目录
mkdir -p outputs/reports outputs/charts outputs/data outputs/json data_cache

# 步骤3：启动应用
echo ""
echo "  ========================================"
echo "  |  正在启动，浏览器将自动打开           |"
echo "  |  http://localhost:8501                |"
echo "  |  Ctrl+C 停止应用                      |"
echo "  ========================================"
echo ""

$PYTHON -m streamlit run app.py --server.headless true --browser.gatherUsageStats false