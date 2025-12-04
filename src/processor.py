import difflib
import re

class Processor:
    def __init__(self):
        self.tag_rules = {
            "manipulation": ["manipulation", "grasping", "picking"],
            "sim2real": ["sim2real", "simulation", "transfer"],
            "locomotion": ["locomotion", "walking", "legged", "quadruped"],
            "navigation": ["navigation", "slam", "path planning"],
            "perception": ["vision", "camera", "depth", "tactile", "sensor"],
            "LLM/VLA": ["language model", "llm", "vla", "transformer", "diffusion", "foundation model"],
            "humanoid": ["humanoid", "bipedal"]
        }

    def clean_text(self, text):
        if not text: return ""
        return re.sub(r'\s+', ' ', text).strip()

    def generate_tags(self, title, abstract):
        text = (title + " " + abstract).lower()
        tags = set()
        for tag, keywords in self.tag_rules.items():
            if any(k in text for k in keywords):
                tags.add(tag)
        return list(tags)

    def is_duplicate(self, title1, title2):
        # 简单去重逻辑：标题相似度 > 0.95
        return difflib.SequenceMatcher(None, title1.lower(), title2.lower()).ratio() > 0.95