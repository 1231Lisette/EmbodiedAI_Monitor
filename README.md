# 🤖 Embodied AI Monitor

**Embodied AI Monitor** 是一个轻量级、跨平台的本地自动化系统，用于每日追踪 **具身智能 (Embodied AI)**、**机器人学习 (Robot Learning)** 以及 **Sim2Real** 领域的最新论文 (arXiv) 和开源项目 (GitHub)。

系统后端基于 Python 自动抓取并清洗数据，前端采用 **Tailwind CSS + Alpine.js** 构建现代化的静态仪表板，无需部署服务器，双击即可在本地浏览。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

## ✨ 功能特性

- **多源数据抓取**：自动聚合 arXiv (cs.RO, cs.AI) 最新论文与 GitHub 热门 Robotics 项目。
- **智能标签化**：基于关键词自动生成 Tags (如 `Sim2Real`, `Manipulation`, `VLA` 等)。
- **零依赖前端**：生成的网页为纯静态文件，支持 **本地双击直接打开**，无需 Nginx/Apache。
- **美观 UI**：基于 Tailwind CSS 设计的响应式仪表板，支持搜索、筛选、排序。
- **双系统支持**：完美兼容 Windows 和 Linux 环境，提供一键运行脚本。

## 🛠️ 技术栈

- **Core**: Python 3.10
- **Data**: arXiv API, GitHub API
- **Web**: Tailwind CSS (CDN), Alpine.js (CDN)
- **Env**: Conda

## 🚀 快速开始

### 1. 环境准备

确保你已安装 [Miniconda](https://docs.conda.io/en/latest/miniconda.html) 或 Anaconda。

```bash
# 1. 克隆仓库
git clone [https://github.com/yourusername/EmbodiedAI_Monitor.git](https://github.com/yourusername/EmbodiedAI_Monitor.git)
cd EmbodiedAI_Monitor

# 2. 创建 Conda 环境
conda create -n embodied_ai python=3.10 -y

# 3. 激活环境
conda activate embodied_ai

# 4. 安装依赖
pip install -r requirements.txt
```

### 2. 配置 (Config)

检查根目录下的 `config.yaml`，你可以自定义抓取的关键词：

```yaml
keywords:
  - "embodied ai"
  - "sim2real"
  - "dexterous manipulation"
  # ... 添加你关注的方向
```

### 3. 运行抓取

在终端中运行主程序：

```bash
python run_scrape.py
```

运行成功后，数据会生成在 `web/data.js`。

### 4. 浏览日报

直接进入 `web/` 文件夹，双击打开 `index.html` 即可查看最新的研究成果。

---

## ⏰ 自动化设置 (每日运行)

系统提供了脚本以支持 Crontab (Linux) 或 Task Scheduler (Windows) 自动运行。

### Linux 用户

1. 编辑 `scripts/run_all.sh`，**务必修改 `CONDA_PATH`** 为你实际的安装路径 (使用 `conda info --base` 查看)。
2. 赋予执行权限：
   ```bash
   chmod +x scripts/run_all.sh
   ```
3. 设置 Crontab (例如每天早上 9 点运行)：
   ```bash
   0 9 * * * /path/to/EmbodiedAI_Monitor/scripts/run_all.sh >> /path/to/EmbodiedAI_Monitor/logs/cron.log 2>&1
   ```

### Windows 用户

1. 直接使用 `scripts/run_all.bat`。
2. 使用 Windows **任务计划程序 (Task Scheduler)** 创建基本任务，指向该 `.bat` 文件即可。

---

## 📂 项目结构

```text
EmbodiedAI_Monitor/
├── config.yaml          # 关键词与参数配置
├── run_scrape.py        # 爬虫主程序
├── web/                 # 前端仪表板
│   ├── index.html       # UI 入口
│   └── data.js          # 生成的数据文件
├── scripts/             # 自动化脚本 (Win/Linux)
└── logs/                # 运行日志
```

## ❓ 常见问题 (Troubleshooting)

**Q: 运行脚本时提示 `source: not found` 或 `conda: command not found`?**
A: 请打开 `scripts/run_all.sh`，确保 `CONDA_PATH` 变量指向了你正确的 Miniconda/Anaconda 安装目录（例如 `/home/username/miniconda3`）。

**Q: 网页打开是空的？**
A: 
1. 确保你已经成功运行了一次 `python run_scrape.py`。
2. 检查 `web/data.js` 文件是否存在且有内容。
3. 检查控制台（F12）是否有报错。

**Q: 报错 `TypeError: 'NoneType' object is not subscriptable`?**
A: 这通常意味着你的 `config.yaml` 是空的或者格式错误。请确保配置文件内容完整。

## 📄 License

本项目采用 [MIT License](LICENSE) 开源。