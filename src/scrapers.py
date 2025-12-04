import requests
import time
import feedparser # 需要安装: pip install feedparser (抱歉requirements漏了，后面补上)
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import urllib.parse
from fake_useragent import UserAgent

class BaseScraper:
    def __init__(self, config):
        self.config = config
        self.ua = UserAgent()
        self.headers = {'User-Agent': self.ua.random}

    def safe_request(self, url, params=None):
        retries = 3
        for i in range(retries):
            try:
                response = requests.get(url, params=params, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    time.sleep(2 ** (i + 1))
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                time.sleep(2)
        return None

class ArxivScraper(BaseScraper):
    def scrape(self):
        papers = []
        base_url = 'http://export.arxiv.org/api/query'
        
        # 搜索查询构建
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

        root = ET.fromstring(resp.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}

        for entry in root.findall('atom:entry', ns):
            paper_id = entry.find('atom:id', ns).text.split('/abs/')[-1]
            title = entry.find('atom:title', ns).text.replace('\n', ' ')
            summary = entry.find('atom:summary', ns).text.replace('\n', ' ')
            authors = [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns)]
            published = entry.find('atom:published', ns).text[:10]
            
            # PDF Link
            pdf_link = ""
            for link in entry.findall('atom:link', ns):
                if link.attrib.get('title') == 'pdf':
                    pdf_link = link.attrib['href']

            papers.append({
                "id": paper_id,
                "title": title,
                "authors": authors,
                "abstract": summary,
                "pdf_url": pdf_link,
                "doi": "",
                "venue": "arXiv",
                "year": int(published[:4]),
                "date": published,
                "keywords": [],
                "tags": [],
                "source": "arxiv"
            })
        return papers

class GithubScraper(BaseScraper):
    def scrape(self):
        projects = []
        token = self.config['api_keys']['github']
        if token:
            self.headers['Authorization'] = f'token {token}'
        
        for topic in self.config['github_topics']:
            url = f"https://api.github.com/search/repositories?q=topic:{topic}&sort=updated&order=desc"
            resp = self.safe_request(url)
            if not resp: continue
            
            items = resp.json().get('items', [])[:self.config['max_github']]
            for item in items:
                projects.append({
                    "id": f"github:{item['full_name']}",
                    "name": item['full_name'],
                    "description": item['description'] or "",
                    "language": item['language'] or "N/A",
                    "stars": item['stargazers_count'],
                    "last_commit_date": item['updated_at'][:10],
                    "readme_url": item['html_url'],
                    "paper_link": item['homepage'],
                    "tags": [topic],
                    "source": "github"
                })
        return projects