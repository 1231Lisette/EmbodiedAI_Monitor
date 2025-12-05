import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class LLMAgent:
    def __init__(self, config):
        self.config = config.get('llm', {})
        # 初始化 OpenAI 客户端
        self.client = None
        if self.config.get('api_key'):
            self.client = OpenAI(
                api_key=self.config['api_key'],
                base_url=self.config.get('base_url', "https://api.deepseek.com")
            )
        else:
            logger.warning("Config 中未找到 llm.api_key，AI 摘要功能将不可用。")

    def generate_summary(self, items):
        if not items or not self.client:
            return ""

        context_text = ""
        for i, item in enumerate(items):
            title = item.get('title', 'No Title')
            source = item.get('source', 'Unknown')
            abstract = item.get('abstract', '')[:200]
            context_text += f"{i+1}. [{source}] {title}\n   Abstract: {abstract}...\n\n"

        prompt = f"""
        你是一个具身智能(Embodied AI)与机器人学习领域的专家研究员。
        请阅读以下今天最热门的 5 篇论文/项目，为我写一段【中文日报摘要】。

        【输入内容】：
        {context_text}

        【输出要求】：
        1. 开头：用**一句话**概括今天的整体技术趋势。
        2. 重点：挑选 2-3 个最有价值的工作进行简短点评。
        3. 格式：对项目名或核心术语使用 **加粗** (Markdown语法)。
        4. 字数：控制在 300 字以内。
        """

        try:
            logger.info(f"正在呼叫 LLM ({self.config.get('model_name')}) 生成摘要...")
            
            response = self.client.chat.completions.create(
                model=self.config.get('model_name'),
                messages=[
                    {"role": "system", "content": "你是一个专业的AI科研助理。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000,
                stream=False
            )
            
            content = response.choices[0].message.content
            logger.info("✅ AI 摘要生成成功！")
            return content.replace('"', '\\"').replace('\n', '\\n')

        except Exception as e:
            logger.error(f"❌ LLM 调用失败: {e}")
            return ""