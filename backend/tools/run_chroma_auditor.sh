#!/bin/bash
# Chroma 向量数据库浏览器启动脚本
# 使用 Gradio UI 查看和检索本地 Chroma 数据库

echo "启动 Chroma 向量数据库浏览器..."
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$BACKEND_DIR"

# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo "提示: 建议在虚拟环境中运行"
    echo "激活虚拟环境: source venv/bin/activate"
    echo ""
fi

# 检查依赖
echo "检查依赖..."
if ! python -c "import gradio" 2>/dev/null; then
    echo "错误: gradio 未安装"
    echo "安装命令: pip install gradio pandas"
    exit 1
fi

if ! python -c "import pandas" 2>/dev/null; then
    echo "错误: pandas 未安装"
    echo "安装命令: pip install pandas"
    exit 1
fi

echo "依赖检查通过"
echo ""
echo "启动 Gradio 服务器..."
echo "访问地址: http://127.0.0.1:7860"
echo "按 Ctrl+C 停止服务器"
echo ""

# 运行工具
python tools/chroma_auditor.py
