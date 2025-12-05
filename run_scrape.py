import os
import yaml
import logging
import requests
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from src.database import Database
from src.scrapers import ArxivScraper, GithubScraper, HuggingFaceScraper
from src.llm_agent import LLMAgent
from src.processor import Processor
import json # 确保导入 json

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def send_email_notification(config, content):
    """发送邮件推送"""
    email_conf = config.get('notification', {}).get('email', {})
    if not config.get('notification', {}).get('enabled'):
        return

    sender = email_conf.get('sender')
    password = email_conf.get('password')
    receiver = email_conf.get('receiver')
    smtp_server = email_conf.get('smtp_server')
    smtp_port = email_conf.get('smtp_port')

    if not all([sender, password, receiver, smtp_server, smtp_port]):
        logger.error("邮件配置不完整，无法发送推送")
        return

    # 构建邮件
    subject = f"🤖 Embodied AI 日报 - {len(content.splitlines())//4} 条精选"
    message = MIMEText(content, 'plain', 'utf-8')
    
    # 使用 formataddr 生成符合 RFC 标准的头部
    message['From'] = formataddr(["AI Monitor", sender])
    message['To'] = formataddr(["Researcher", receiver])
    message['Subject'] = Header(subject, 'utf-8')

    try:
        logger.info("正在发送邮件...")
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        
        server.login(sender, password)
        server.sendmail(sender, [receiver], message.as_string())
        server.quit()
        logger.info("✅ 邮件发送成功！请检查收件箱")
    except Exception as e:
        logger.error(f"❌ 邮件发送失败: {e}")

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.yaml')
    
    if not os.path.exists(config_path):
        logger.error("找不到 config.yaml！")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    db = Database()
    llm = LLMAgent(config)
    tagger = Processor()

    items_to_process = []

    # 1. 抓取 (ArXiv)
    logger.info("🚀 开始抓取 ArXiv...")
    for p in ArxivScraper(config).scrape():
        p['type'] = 'papers'
        items_to_process.append(p)

    # 2. 抓取 (GitHub)
    logger.info("🚀 开始抓取 GitHub...")
    for p in GithubScraper(config).scrape():
        p['type'] = 'projects'
        # GitHub 预览图
        p['media_url'] = f"https://opengraph.githubassets.com/1/{p['id'].replace('github:', '')}"
        items_to_process.append(p)

    # 3. 抓取 (Hugging Face)
    logger.info("🚀 开始抓取 Hugging Face...")
    for p in HuggingFaceScraper(config).scrape():
        p['type'] = 'models'
        items_to_process.append(p)

    # 4. AI 审稿
    logger.info(f"🧠 AI 正在评审 {len(items_to_process)} 条内容...")
    
    all_tags = set()

    for item in items_to_process:
        # 生成标签
        item['tags'] = tagger.generate_tags(item['title'], item['abstract'])
        for t in item['tags']:
            all_tags.add(t)
        
        # 调用 LLM 打分
        score, comment = llm.review_item(item['title'], item['abstract'], item['source'])
        item['ai_score'] = score
        item['ai_comment'] = comment
        
        print(f"   [{score}分] {item['title'][:40]}... | {comment}")
        
        # 存入数据库
        db.upsert_item(item)

    # 5. 生成日报并推送
    top_items = db.fetch_items(min_score=6) 
    
    if top_items:
        logger.info(f"找到 {len(top_items)} 条高分内容，准备生成日报...")
        report = llm.generate_daily_report(top_items)
        send_email_notification(config, report)
    else:
        logger.info("今日没有高分内容，不打扰了。")
        
    # 6. 生成 JS 数据文件
    items_to_process.sort(key=lambda x: x.get('ai_score', 0), reverse=True)
    
    daily_summary_text = report if 'report' in locals() else "今日无高分更新"
    
    # --- 修复部分：先处理字符串，再放入 f-string ---
    safe_summary = daily_summary_text.replace('"', '\\"').replace('\n', '\\n')
    
    js_content = f"""
    window.RESEARCH_DATA = {json.dumps(items_to_process, ensure_ascii=False)};
    window.ALL_TAGS = {json.dumps(list(all_tags), ensure_ascii=False)};
    window.DAILY_SUMMARY = "{safe_summary}";
    window.LAST_UPDATE = "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}";
    """
    
    web_dir = os.path.join(base_dir, 'web')
    os.makedirs(web_dir, exist_ok=True)
    with open(os.path.join(web_dir, 'data.js'), 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    db.close()
    logger.info("🎉 任务完成！")

if __name__ == "__main__":
    main()