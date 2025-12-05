import requests
import time
import feedparser
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from fake_useragent import UserAgent
from huggingface_hub import HfApi # 修正：移除了 ModelFilter

class BaseScraper:
    def __init__(self, config):
        self.config = config
        self.ua = UserAgent()
        self.headers = {'User-Agent': self.ua.random}

    def safe_request(self, url, params=None):
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        return None

    def calculate_score(self, text):
        text = text.lower()
        score = 0
        scoring_rules = self.config.get('interest_scoring', {})
        
        for kw in scoring_rules.get('high', []):
            if kw in text: score += 3
            
        for kw in scoring_rules.get('medium', []):
            if kw in text: score += 1
            
        return score

class ArxivScraper(BaseScraper):
    def scrape(self):
        papers = []
        base_url = 'http://export.arxiv.org/api/query'
        
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
        
        resp = self.safe_request(base_url, params)
        if not resp: return []

        try:
            root = ET.fromstring(resp.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text.replace('\n', ' ')
                summary = entry.find('atom:summary', ns).text.replace('\n', ' ')
                
                relevance_score = self.calculate_score(title + " " + summary)
                
                pdf_link = ""
                for link in entry.findall('atom:link', ns):
                    if link.get('title') == 'pdf':
                        pdf_link = link.attrib['href']
                        break

                papers.append({
                    "id": entry.find('atom:id', ns).text.split('/abs/')[-1],
                    "type": "papers",
                    "title": title,
                    "author": ", ".join([a.find('atom:name', ns).text for a in entry.findall('atom:author', ns)][:3]),
                    "abstract": summary,
                    "date": entry.find('atom:published', ns).text[:10],
                    "url": pdf_link,
                    "score": relevance_score,
                    "tags": [], # 留给主程序生成
                    "source": "arXiv"
                })
        except Exception as e:
            print(f"Arxiv Parse Error: {e}")
        
        return papers

class GithubScraper(BaseScraper):
    def scrape(self):
        projects = []
        for topic in self.config['github_topics']:
            url = f"https://api.github.com/search/repositories?q=topic:{topic}+stars:>10&sort=updated&order=desc"
            resp = self.safe_request(url)
            if not resp: continue
            
            items = resp.json().get('items', [])[:10]
            for item in items:
                desc = item['description'] or ""
                score = self.calculate_score(item['full_name'] + " " + desc)
                if item['stargazers_count'] > 1000: score += 2
                if item['stargazers_count'] > 5000: score += 3

                projects.append({
                    "id": str(item['id']),
                    "type": "projects",
                    "title": item['full_name'],
                    "author": item['owner']['login'],
                    "abstract": desc,
                    "date": item['updated_at'][:10],
                    "url": item['html_url'],
                    "stars": item['stargazers_count'],
                    "score": score,
                    "tags": [],
                    "source": "GitHub"
                })
        
        # 简单去重
        seen = set()
        unique_projects = []
        for p in projects:
            if p['id'] not in seen:
                seen.add(p['id'])
                unique_projects.append(p)
        
        return unique_projects

class HuggingFaceScraper(BaseScraper):
    def scrape(self):
        models = []
        api = HfApi()
        seen_ids = set()
        
        # 1. 获取 Trending Models
        # 修正逻辑：遍历 config 中的每个 task，分别获取热门，然后去重
        tasks = self.config.get('huggingface', {}).get('tasks', ['robotics'])
        
        for task in tasks:
            try:
                # 直接传字符串作为 filter，不再使用 ModelFilter
                trending = api.list_models(
                    filter=task, 
                    sort="likes7d",
                    direction=-1,
                    limit=5 
                )
                
                for m in trending:
                    if m.modelId in seen_ids: continue
                    seen_ids.add(m.modelId)

                    score = 5 + self.calculate_score(m.modelId)
                    
                    models.append({
                        "id": m.modelId,
                        "type": "models",
                        "title": m.modelId,
                        "author": m.author if m.author else m.modelId.split('/')[0],
                        "abstract": f"🔥 Trending on HF ({m.likes} likes). Task: {m.pipeline_tag}",
                        "date": str(m.lastModified)[:10],
                        "url": f"https://huggingface.co/{m.modelId}",
                        "stars": m.likes,
                        "score": score,
                        "tags": m.tags if m.tags else [],
                        "source": "HuggingFace"
                    })
            except Exception as e:
                print(f"HF Task {task} Error: {e}")

        # 2. 重点关注的大厂/实验室
        orgs = self.config.get('huggingface', {}).get('orgs', [])
        for org in orgs:
            try:
                org_models = api.list_models(
                    author=org,
                    sort="lastModified",
                    direction=-1,
                    limit=3 
                )
                for m in org_models:
                    last_mod = str(m.lastModified)[:10]
                    # 只看最近 7 天的
                    try:
                        delta = datetime.now() - datetime.strptime(last_mod, "%Y-%m-%d")
                        if delta.days > 7: continue
                    except:
                        pass
                    
                    if m.modelId in seen_ids: continue
                    seen_ids.add(m.modelId)
                            
                    models.append({
                        "id": m.modelId,
                        "type": "models",
                        "title": m.modelId,
                        "author": org,
                        "abstract": f"🏛️ Official release from {org}. Task: {m.pipeline_tag}",
                        "date": last_mod,
                        "url": f"https://huggingface.co/{m.modelId}",
                        "stars": m.likes,
                        "score": 10,
                        "tags": m.tags if m.tags else [],
                        "source": "HuggingFace"
                    })
            except Exception as e:
                print(f"HF Org {org} Error: {e}")
            
        return models