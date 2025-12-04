import sqlite3
import json
import os
from datetime import datetime

class Database:
    def __init__(self, db_path="data/papers.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        # 论文表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS papers (
                id TEXT PRIMARY KEY,
                title TEXT,
                authors TEXT,
                abstract TEXT,
                pdf_url TEXT,
                doi TEXT,
                venue TEXT,
                year INTEGER,
                date TEXT,
                keywords TEXT,
                tags TEXT,
                code_link TEXT,
                source TEXT,
                fetched_at TEXT
            )
        ''')
        # GitHub 项目表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                language TEXT,
                stars INTEGER,
                last_commit_date TEXT,
                readme_url TEXT,
                paper_link TEXT,
                tags TEXT,
                source TEXT,
                fetched_at TEXT
            )
        ''')
        # 全文索引 (FTS5)
        cursor.execute('CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(title, abstract, content="papers", content_rowid="rowid")')
        self.conn.commit()

    def upsert_paper(self, paper):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO papers (id, title, authors, abstract, pdf_url, doi, venue, year, date, keywords, tags, code_link, source, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                code_link = COALESCE(excluded.code_link, papers.code_link),
                tags = excluded.tags
        ''', (
            paper['id'], paper['title'], json.dumps(paper['authors']), paper['abstract'],
            paper['pdf_url'], paper['doi'], paper['venue'], paper['year'], paper['date'],
            json.dumps(paper['keywords']), json.dumps(paper['tags']), paper.get('code_link'),
            paper['source'], datetime.now().isoformat()
        ))
        # 更新索引
        cursor.execute('INSERT INTO papers_fts(papers_fts) VALUES("rebuild")')
        self.conn.commit()

    def upsert_project(self, proj):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO projects (id, name, description, language, stars, last_commit_date, readme_url, paper_link, tags, source, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                stars = excluded.stars,
                last_commit_date = excluded.last_commit_date
        ''', (
            proj['id'], proj['name'], proj['description'], proj['language'], proj['stars'],
            proj['last_commit_date'], proj['readme_url'], proj.get('paper_link'),
            json.dumps(proj['tags']), proj['source'], datetime.now().isoformat()
        ))
        self.conn.commit()

    def fetch_all_data(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM papers ORDER BY date DESC LIMIT 1000")
        papers = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM projects ORDER BY stars DESC LIMIT 500")
        projects = [dict(row) for row in cursor.fetchall()]
        
        # JSON 转换
        for p in papers:
            p['authors'] = json.loads(p['authors']) if p['authors'] else []
            p['keywords'] = json.loads(p['keywords']) if p['keywords'] else []
            p['tags'] = json.loads(p['tags']) if p['tags'] else []
            
        for p in projects:
            p['tags'] = json.loads(p['tags']) if p['tags'] else []

        return {"papers": papers, "projects": projects}

    def close(self):
        self.conn.close()