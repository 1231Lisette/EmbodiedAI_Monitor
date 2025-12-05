#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$DIR/.."
cd "$PROJECT_ROOT"

echo "=========================================="
echo "Running Embodied AI Monitor"
echo "Time: $(date)"
echo "=========================================="

# 自动查找并初始化 conda
# 请根据你的实际安装路径修改 CONDA_PATH
CONDA_PATH="/home/pyy/miniconda3"
source "$CONDA_PATH/etc/profile.d/conda.sh"

conda activate embodied_ai

export https_proxy=http://127.0.0.1:7897
export http_proxy=http://127.0.0.1:7897


# 1. 先运行抓取和 AI 评审
echo "正在抓取并生成日报..."
python run_scrape.py

# 2. 抓取成功后，自动启动 Streamlit 网页
if [ $? -eq 0 ]; then
    echo "[SUCCESS] 数据更新完毕，正在启动交互式看板..."
    # 自动打开浏览器查看
    streamlit run app.py
else
    echo "[ERROR] 抓取失败，请检查日志。"
fi