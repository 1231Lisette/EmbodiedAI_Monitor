import sqlite3
import json
import os
from datetime import datetime

class Database:
    def __init__(self, db_path="data/papers.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        # 统一的一张表存储所有类型的资源，方便管理
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                type TEXT,          -- papers, projects, models
                source TEXT,        -- arxiv, github, huggingface
                title TEXT,
                author TEXT,
                abstract TEXT,
                url TEXT,
                date TEXT,
                tags TEXT,          -- JSON list
                
                -- V2.0 新增字段
                ai_score REAL DEFAULT 0,      -- AI 打分 (0-10)
                ai_comment TEXT,              -- AI 短评
                media_url TEXT,               -- 预览图/视频链接
                is_read INTEGER DEFAULT 0,    -- 是否已读
                is_star INTEGER DEFAULT 0,    -- 是否星标/稍后读
                user_notes TEXT,              -- 用户笔记
                fetched_at TEXT
            )
        ''')
        # 全文索引
        cursor.execute('CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(title, abstract, ai_comment, content="items", content_rowid="rowid")')
        self.conn.commit()

    def upsert_item(self, item):
        cursor = self.conn.cursor()
        # 只更新基本信息，保留用户的笔记和状态
        cursor.execute('''
            INSERT INTO items (id, type, source, title, author, abstract, url, date, tags, ai_score, ai_comment, media_url, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                ai_score = COALESCE(excluded.ai_score, items.ai_score),
                ai_comment = COALESCE(excluded.ai_comment, items.ai_comment),
                media_url = COALESCE(excluded.media_url, items.media_url),
                fetched_at = excluded.fetched_at
        ''', (
            item['id'], item['type'], item['source'], item['title'], item['author'], 
            item['abstract'], item['url'], item['date'], json.dumps(item.get('tags', [])),
            item.get('ai_score', 0), item.get('ai_comment', ""), item.get('media_url', ""),
            datetime.now().isoformat()
        ))
        cursor.execute('INSERT INTO items_fts(items_fts) VALUES("rebuild")')
        self.conn.commit()

    def update_user_interaction(self, item_id, is_read=None, is_star=None, notes=None):
        """更新用户交互状态"""
        cursor = self.conn.cursor()
        if is_read is not None:
            cursor.execute("UPDATE items SET is_read = ? WHERE id = ?", (is_read, item_id))
        if is_star is not None:
            cursor.execute("UPDATE items SET is_star = ? WHERE id = ?", (is_star, item_id))
        if notes is not None:
            cursor.execute("UPDATE items SET user_notes = ? WHERE id = ?", (notes, item_id))
        self.conn.commit()

    def fetch_items(self, days=7, min_score=0):
        """获取最近 N 天且分数大于 X 的内容"""
        cursor = self.conn.cursor()
        # 简单的日期过滤逻辑可以根据需求增强
        cursor.execute(f'''
            SELECT * FROM items 
            WHERE ai_score >= ? 
            ORDER BY date DESC, ai_score DESC 
            LIMIT 500
        ''', (min_score,))
        items = [dict(row) for row in cursor.fetchall()]
        for i in items:
            i['tags'] = json.loads(i['tags']) if i['tags'] else []
        return items

    def close(self):
        self.conn.close()