import os
import json
import time
import yaml
import requests
import feedparser
import logging
from datetime import datetime
from fake_useragent import UserAgent

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

# --- 爬虫类 ---
class Scraper:
    def __init__(self, config):
        self.config = config
        self.ua = UserAgent()
        self.tagger = TagGenerator()

    def fetch_arxiv(self):
        logger.info("正在抓取 arXiv...")
        papers = []
        base_url = 'http://export.arxiv.org/api/query'
        
        # 构建查询
        terms = [f'all:"{k}"' for k in self.config['keywords']]
        query = " OR ".join(terms)
        query += ' AND (cat:cs.RO OR cat:cs.AI OR cat:cs.CV)'
        
        params = {
            'search_query': query,
            'start': 0,
            'max_results': self.config['max_arxiv'],
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }

        try:
            resp = requests.get(base_url, params=params, timeout=20)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.content)
                for entry in feed.entries:
                    # --- 修复开始: 安全获取 PDF 链接 ---
                    pdf_link = ""
                    if hasattr(entry, 'links'):
                        for link in entry.links:
                            # 使用 .get() 安全获取 title，防止报错
                            if link.get('title') == 'pdf':
                                pdf_link = link.href
                                break
                    # --- 修复结束 ---
                    
                    # 安全获取其他字段，防止某个字段缺失导致崩溃
                    papers.append({
                        "id": entry.id.split('/')[-1],
                        "type": "papers",
                        "title": entry.get('title', 'No Title').replace('\n', ' '),
                        "author": ", ".join(a.name for a in entry.authors[:3]) if hasattr(entry, 'authors') else "Unknown",
                        "abstract": entry.get('summary', '').replace('\n', ' '),
                        "date": entry.published[:10] if hasattr(entry, 'published') else "",
                        "url": pdf_link,
                        "tags": self.tagger.get_tags(entry.get('title', '') + " " + entry.get('summary', '')),
                        "source": "arXiv"
                    })
        except Exception as e:
            # 打印详细错误位置，方便调试
            logger.error(f"arXiv抓取失败: {e}", exc_info=True)
        
        return papers

    def fetch_github(self):
        logger.info("正在抓取 GitHub...")
        projects = []
        headers = {'User-Agent': self.ua.random}
        
        for topic in self.config['github_topics']:
            url = f"https://api.github.com/search/repositories?q=topic:{topic}&sort=updated&order=desc"
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    items = resp.json().get('items', [])[:self.config['max_github']]
                    for item in items:
                        desc = item['description'] or ""
                        projects.append({
                            "id": str(item['id']),
                            "type": "projects",
                            "title": item['full_name'],
                            "author": item['owner']['login'], # GitHub Owner 作为 Author
                            "abstract": desc,
                            "date": item['updated_at'][:10],
                            "url": item['html_url'],
                            "stars": item['stargazers_count'],
                            "language": item['language'] or "N/A",
                            "tags": [item['language']] + self.tagger.get_tags(item['full_name'] + " " + desc),
                            "source": "GitHub"
                        })
                time.sleep(1) # 避免触发速率限制
            except Exception as e:
                logger.error(f"GitHub抓取失败: {e}")
        
        # 简单去重
        unique_projects = {p['id']: p for p in projects}.values()
        return list(unique_projects)

# --- 主程序逻辑 ---
def main():
    # 1. 读取配置
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, 'config.yaml'), 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 2. 抓取数据
    scraper = Scraper(config)
    data_papers = scraper.fetch_arxiv()
    data_projects = scraper.fetch_github()
    
    # 合并数据
    all_data = data_papers + data_projects
    logger.info(f"抓取完成: {len(data_papers)} 篇论文, {len(data_projects)} 个项目")

    # 3. 提取所有出现的标签 (用于前端过滤)
    all_tags = set()
    for item in all_data:
        for t in item['tags']:
            if t: all_tags.add(t)
    
    # 4. 生成 JS 数据文件
    # 我们将数据注入到一个全局变量 window.RESEARCH_DATA 中
    js_content = f"""
    window.RESEARCH_DATA = {json.dumps(all_data, ensure_ascii=False)};
    window.ALL_TAGS = {json.dumps(list(all_tags), ensure_ascii=False)};
    window.LAST_UPDATE = "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}";
    """
    
    web_dir = os.path.join(base_dir, 'web')
    os.makedirs(web_dir, exist_ok=True)
    
    with open(os.path.join(web_dir, 'data.js'), 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    logger.info(f"数据已生成至: {os.path.join(web_dir, 'data.js')}")

if __name__ == "__main__":
    main()