import re
from typing import Dict, Any, List
from app.scenes.base import BaseScene

class InterviewScene(BaseScene):
    """
    软件工程师技术面试场景插件。
    """

    @property
    def scene_id(self) -> str:
        return "interview"

    @property
    def name(self) -> str:
        return "软件工程师面试 (Job Interview)"

    @property
    def description(self) -> str:
        return "模拟外企软件工程师英文技术面试，考察专业术语、沟通能力与逻辑表达。"

    @property
    def category(self) -> str:
        return "business"

    @property
    def default_params(self) -> Dict[str, Any]:
        return {
            "personality": "professional and slightly strict",  # 性格：专业且稍显严厉
            "company_name": "Global Tech Inc.",                  # 公司名称
            "job_title": "Senior Frontend Developer",            # 应聘职位
            "interviewer_name": "Sarah"                         # 面试官名字
        }

    @property
    def system_prompt_template(self) -> str:
        return (
            "You are {interviewer_name}, a professional and {personality} Senior engineering manager at {company_name}. "
            "You are conducting a job interview with the candidate (the user) for the {job_title} position. "
            "Speak naturally as a native English speaker. Ask technical frontend questions (e.g., React/Vue lifecycle, performance optimization, CSS layouts) "
            "and behavioral questions. Ask only ONE question at a time to allow a realistic conversation flow. "
            "Keep your responses concise (1-2 sentences). Do not repeat the same questions."
        )

    def get_greeting(self, custom_params: Dict[str, Any] = None) -> str:
        params = self.default_params.copy()
        if custom_params:
            for k, v in custom_params.items():
                if k in params:
                    params[k] = v
        
        return (
            f"Hello! Welcome to {params['company_name']}. I am {params['interviewer_name']}, and I will be "
            f"conducting your technical interview for the {params['job_title']} position today. "
            f"To start, could you please briefly introduce yourself and highlight some of your core frontend achievements?"
        )

    def validate_turn(self, user_input: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        # 规则 1：检查是否含有大量中文（比如超过3个连续汉字）
        if re.search(r'[\u4e00-\u9fa5]{3,}', user_input):
            return {
                "is_valid": True,  # 放行，但给予警告提示
                "warning": "温馨提示：面试官 Sarah 仅支持英文交流。在技术面试中，请尽量使用英文阐述您的技术栈和项目经验。",
                "modified_input": user_input
            }
            
        # 规则 2：如果字数过少（少于 3 个单词），可能是应答不完整
        word_count = len(user_input.split())
        if word_count < 3 and len(user_input.strip()) > 0:
            return {
                "is_valid": True,
                "warning": "您的回答非常简短。在真实的面试中，建议通过提供更多项目细节（如技术选型、遇到的困难及如何解决）来丰富回答。",
                "modified_input": user_input
            }

        return {
            "is_valid": True,
            "warning": "",
            "modified_input": user_input
        }

    def get_evaluation_rules(self) -> str:
        return (
            "1. 评估用户在前端开发（如框架原理、浏览器渲染、优化策略）等专业英文术语表达上的准确性。\n"
            "2. 评估用户在回答行为面试题（Behavioral Questions）时是否符合 STAR 法则（情境-任务-行动-结果）逻辑。\n"
            "3. 评估用户的职场英语礼仪与表达得体度。"
        )
