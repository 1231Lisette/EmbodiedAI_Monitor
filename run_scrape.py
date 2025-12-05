import os
import json
import time
import yaml
import requests
import feedparser
import logging
from datetime import datetime
from fake_useragent import UserAgent
# 引入我们写好的模块
from src.scrapers import ArxivScraper, GithubScraper, HuggingFaceScraper
from src.llm_agent import LLMAgent

# --- 配置日志 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 工具类：生成标签 ---
class TagGenerator:
    def __init__(self):
        self.rules = {
            "Sim2Real": ["sim2real", "simulation", "transfer"],
            "Manipulation": ["manipulation", "grasping", "pick and place", "dexterous"],
            "Locomotion": ["locomotion", "walking", "legged", "quadruped"],
            "Vision": ["vision", "camera", "depth", "perception", "3d"],
            "LLM/VLA": ["language model", "llm", "vla", "transformer", "foundation model"],
            "Humanoid": ["humanoid", "bipedal"],
            "Reinforcement": ["reinforcement learning", "rl", "policy"]
        }

    def get_tags(self, text):
        text = text.lower()
        tags = set()
        for tag, keywords in self.rules.items():
            if any(k in text for k in keywords):
                tags.add(tag)
        return list(tags) if tags else ["General"]

# --- 主程序逻辑 ---
def main():
    # 1. 读取配置
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.yaml')
    
    if not os.path.exists(config_path):
        logger.error("找不到 config.yaml！")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 2. 抓取数据
    tagger = TagGenerator()
    
    # --- ArXiv ---
    arxiv_scraper = ArxivScraper(config)
    data_papers = arxiv_scraper.scrape()
    for p in data_papers:
        p['tags'] = tagger.get_tags(p['title'] + " " + p['abstract'])

    # --- GitHub ---
    gh_scraper = GithubScraper(config)
    data_projects = gh_scraper.scrape()
    for p in data_projects:
        p['tags'] = tagger.get_tags(p['title'] + " " + p['abstract'])

    # --- Hugging Face ---
    logger.info("正在抓取 Hugging Face...")
    hf_scraper = HuggingFaceScraper(config)
    data_models = hf_scraper.scrape()
    for m in data_models:
        custom_tags = tagger.get_tags(m['title'])
        m['tags'] = list(set(m['tags'] + custom_tags))

    # 3. 合并数据 & 排序
    all_data = data_papers + data_projects + data_models
    all_data.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    logger.info(f"抓取完成: {len(data_papers)} 论文, {len(data_projects)} 项目, {len(data_models)} 模型")

    # ==========================================
    # 4. [关键修复] 优先生成标签 (绝对安全的操作)
    # ==========================================
    all_tags = set()
    for item in all_data:
        for t in item['tags']:
            if t: all_tags.add(t)

    # ==========================================
    # 5. [防爆处理] 生成 AI 摘要 (高风险操作)
    # ==========================================
    daily_summary = ""
    try:
        # 只有当数据不为空时才调用 LLM
        if all_data:
            llm_bot = LLMAgent(config)
            # 只取前 5 个最重要的数据
            top_items = all_data[:5] 
            daily_summary = llm_bot.generate_summary(top_items)
        else:
            logger.warning("数据为空，跳过 AI 摘要。")
            
    except Exception as e:
        # 这里捕获所有错误（包括 401 密钥错误），只打印日志，绝对不让程序崩！
        logger.error(f"⚠️ AI 摘要生成失败 (不影响网页生成): {e}")
        daily_summary = "（由于网络或配置原因，今日 AI 摘要暂时不可用，请检查日志。）"

    # 6. 生成 JS 数据文件
    # 此时 all_tags 和 daily_summary 都有值了（哪怕是空值），绝对不会报 NameError
    js_content = f"""
    window.RESEARCH_DATA = {json.dumps(all_data, ensure_ascii=False)};
    window.ALL_TAGS = {json.dumps(list(all_tags), ensure_ascii=False)};
    window.DAILY_SUMMARY = "{daily_summary}";
    window.LAST_UPDATE = "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}";
    """
    
    web_dir = os.path.join(base_dir, 'web')
    os.makedirs(web_dir, exist_ok=True)
    
    with open(os.path.join(web_dir, 'data.js'), 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    logger.info(f"✅ 数据已成功生成至: {os.path.join(web_dir, 'data.js')}")

if __name__ == "__main__":
    main()