import re
from typing import Dict, Any, List
from app.scenes.base import BaseScene

class MeetingScene(BaseScene):
    """
    商务同步会议场景插件。
    """

    @property
    def scene_id(self) -> str:
        return "meeting"

    @property
    def name(self) -> str:
        return "产品发布会同步会议 (Business Meeting)"

    @property
    def description(self) -> str:
        return "参与跨国项目组的产品发布准备会议，讨论进度延误、解决方案与任务分工。"

    @property
    def category(self) -> str:
        return "business"

    @property
    def default_params(self) -> Dict[str, Any]:
        return {
            "personality": "result-oriented and collaborative",   # 性格：结果导向且乐于协作
            "chairperson_name": "David",                          # 会议主持/PM名字
            "topic": "Frontend delay for the Q3 product launch",  # 会议议题
            "urgency": "high"                                     # 紧急程度
        }

    @property
    def system_prompt_template(self) -> str:
        return (
            "You are {chairperson_name}, the Product Manager leading a Q3 product launch alignment meeting. "
            "The user is a frontend developer on your team. The meeting topic is: {topic}. Urgency level: {urgency}. "
            "Speak professionally, using polite but direct business English. Ask the developer about progress, "
            "reasons for the delay, blockages, and potential solutions. "
            "Keep responses concise (1-2 sentences) and request concrete estimations. Ask one question at a time."
        )

    def get_greeting(self, custom_params: Dict[str, Any] = None) -> str:
        params = self.default_params.copy()
        if custom_params:
            for k, v in custom_params.items():
                if k in params:
                    params[k] = v
        
        return (
            f"Hi team, thanks for joining. Let's get straight to the point. We are here to align on the "
            f"{params['topic']}. As you know, the urgency is {params['urgency']}. "
            f"Could you explain the current status on your side and what main blockages are causing the delay?"
        )

    def validate_turn(self, user_input: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        # 商务会议中字数较少可能显示沟通不畅
        word_count = len(user_input.split())
        if word_count < 4 and len(user_input.strip()) > 0:
            return {
                "is_valid": True,
                "warning": "温馨提示：在商务进度汇报中，建议提供具体的细节（如具体模块、调试进展或协调配合），用以表现专业精神和协作态度。",
                "modified_input": user_input
            }
            
        return {
            "is_valid": True,
            "warning": "",
            "modified_input": user_input
        }

    def get_evaluation_rules(self) -> str:
        return (
            "1. 评估用户是否能准确描述技术问题和时间进度（如：bottleneck, eta, delay, deployment, resource 等词汇的使用）。\n"
            "2. 评估用户在面对压力/质疑（如项目延期）时的英语沟通策略，是否具备积极解决问题的语气。\n"
            "3. 评估用户的商业陈述逻辑度与职场用语规范度。"
        )
