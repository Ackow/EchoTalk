from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseScene(ABC):
    """
    口语演练场景抽象基类。所有具体场景插件（面试、点餐等）都必须继承该类，
    并实现相关的元数据和自定义规则逻辑。
    """

    @property
    @abstractmethod
    def scene_id(self) -> str:
        """
        场景唯一标识 ID（例如：'interview'）
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        场景展示名称
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        场景描述
        """
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        """
        场景分类（如 'business', 'daily', 'academic'）
        """
        pass

    @property
    @abstractmethod
    def default_params(self) -> Dict[str, Any]:
        """
        场景默认的可配置参数字典（例如：人物性格、天气、限定词等）
        """
        pass

    @property
    @abstractmethod
    def system_prompt_template(self) -> str:
        """
        系统提示词模板（支持大括号 `{variable}` 占位符，由具体场景自定义参数渲染）
        """
        pass

    def get_system_prompt(self, custom_params: Dict[str, Any] = None) -> str:
        """
        根据传入的自定义参数，渲染并生成发送给大模型的 System Prompt。
        如果没有传自定义参数，则采用场景默认参数。
        """
        params = self.default_params.copy()
        if custom_params:
            # 合并自定义参数，只更新已有的 Key
            for k, v in custom_params.items():
                if k in params:
                    params[k] = v
        
        try:
            return self.system_prompt_template.format(**params)
        except KeyError as e:
            # 容错：如果格式化时缺少了某个 key，输出未渲染的模板，避免系统崩溃
            print(f"[警告] 场景提示词模板渲染缺失 Key: {e}")
            return self.system_prompt_template

    @abstractmethod
    def get_greeting(self, custom_params: Dict[str, Any] = None) -> str:
        """
        获取场景的初始问候语（AI 说的第一句话）。
        由于首句不经过大模型生成以降低首次交互延迟，因此通过此方法硬编码渲染或直接返回。
        """
        pass

    def validate_turn(self, user_input: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        交互拦截校验钩子。
        在用户的转录文本发送给大模型之前，校验是否符合角色扮演设定或存在异常输入。
        
        返回值格式：
        {
            "is_valid": bool,        # 校验是否通过
            "warning": str,          # 警告/提示语（用于前端浮现提示用户，例如 '请尝试使用英语回答哦！'）
            "modified_input": str    # 修改后的输入（例如去除敏感词、标点修剪，默认等于原输入）
        }
        """
        # 默认实现：不进行额外拦截，直接放行
        return {
            "is_valid": True,
            "warning": "",
            "modified_input": user_input
        }

    def get_evaluation_rules(self) -> str:
        """
        获取该场景专属的课后总结评估准则（提示词片段）。
        大模型在生成课后报告时会拼入此准则，使得评估维度更贴近场景特色（例如：面试场景侧重专业词汇与逻辑，点餐场景侧重日常表达）。
        """
        return "请针对用户的语法准确性、用词得体度、句子流畅性进行评价。"
