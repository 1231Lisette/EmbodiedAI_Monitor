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

python run_scrape.py

if [ $? -eq 0 ]; then
    echo "[SUCCESS] Data generated."
else
    echo "[ERROR] Failed."
fi