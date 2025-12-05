import logging
import json
import re
from datetime import datetime  # <--- 之前就是缺了这一行！
from openai import OpenAI

logger = logging.getLogger(__name__)

class LLMAgent:
    def __init__(self, config):
        self.config = config.get('llm', {})
        self.client = None
        if self.config.get('api_key'):
            self.client = OpenAI(
                api_key=self.config['api_key'],
                base_url=self.config.get('base_url')
            )

    def review_item(self, title, abstract, source):
        """
        AI 审稿人：对单篇内容进行评分和点评
        """
        if not self.client: return 0, "LLM未配置"

        prompt = f"""
        你是一个苛刻的具身智能(Embodied AI)领域审稿人。
        请评估以下{source}内容：
        标题：{title}
        摘要：{abstract[:800]}

        请以JSON格式输出以下字段（不要Markdown，只要纯JSON）：
        1. "score": 整数(0-10)。打分标准：
           - 9-10: 突破性工作，必读（如新的SOTA架构、极大降低成本、开源了高质量数据/硬件）。
           - 7-8: 有趣且扎实的工作，值得关注。
           - 4-6: 常规工作，或者是纯理论/无实验。
           - 0-3: 与具身智能/机器人无关，或质量极低。
        2. "comment": 字符串(中文)。用一句话犀利点评，直击痛点或亮点（例如："提出了基于VLA的新架构，但缺乏实机实验" 或 "开源了低成本机械臂清单，极具复现价值"）。
        """

        try:
            response = self.client.chat.completions.create(
                model=self.config.get('model_name'),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            # 清洗一下可能存在的 markdown 标记
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            data = json.loads(content.strip())
            return data.get('score', 5), data.get('comment', '无评价')
        except Exception as e:
            logger.error(f"评审失败: {e}")
            return 0, "评审出错"

    def generate_daily_report(self, top_items):
        """生成日报推送文案"""
        if not top_items: return "今日无重要更新。"
        
        lines = ["🤖 Embodied AI 日报"]
        # 这里使用了 datetime，所以开头必须导入它
        lines.append(f"📅 {datetime.now().strftime('%Y-%m-%d')}\n")
        
        for i, item in enumerate(top_items[:10]): 
            score_emoji = "🔥" if item.get('ai_score', 0) >= 8 else "⭐"
            lines.append(f"{i+1}. {score_emoji} [{item['ai_score']}分] {item['title']}")
            lines.append(f"   💡 {item['ai_comment']}")
            lines.append(f"   🔗 {item['url']}\n")
            
        return "\n".join(lines)