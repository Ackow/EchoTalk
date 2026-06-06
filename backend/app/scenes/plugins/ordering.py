import re
from typing import Dict, Any, List
from app.scenes.base import BaseScene

class OrderingScene(BaseScene):
    """
    咖啡厅日常点单场景插件。
    """

    @property
    def scene_id(self) -> str:
        return "ordering"

    @property
    def name(self) -> str:
        return "繁忙咖啡厅点餐 (Cafe Ordering)"

    @property
    def description(self) -> str:
        return "在纽约街头咖啡馆点一份早餐与咖啡，练习日常口语、定制化订单与结账表达。"

    @property
    def category(self) -> str:
        return "daily"

    @property
    def default_params(self) -> Dict[str, Any]:
        return {
            "personality": "friendly but busy",               # 性格：友好但非常忙碌
            "store_name": "Metro Cafe",                       # 店名
            "cashier_name": "Leo",                            # 收银/咖啡师名字
            "out_of_stock_item": "croissants"                 # 缺货商品（用于练习应变口语）
        }

    @property
    def system_prompt_template(self) -> str:
        return (
            "You are {cashier_name}, a friendly but very busy barista at {store_name} in New York. "
            "The customer (user) is ordering drinks or food. Ask for preferences like cup size (small, medium, large), "
            "milk choices (oat, almond, skim, whole), or to-go/for-here. "
            "IMPORTANT: Today we are completely out of {out_of_stock_item}. If the customer asks for it, "
            "apologize politely and recommend blueberry muffins or chocolate bagels instead. "
            "CRITICAL: When the customer asks for the bill or you provide the final price, you MUST calculate the total price strictly and mathematically using the menu prices provided in the RAG knowledge base (including size base prices and milk/pastry surcharges). Do not hallucinate or make up estimated prices. "
            "To simulate a busy morning queue, keep your responses extremely short (1 sentence, max 15 words). "
            "Once their food and drink items are finalized, request payment (cash or card) to end the transaction."
        )

    def get_greeting(self, custom_params: Dict[str, Any] = None) -> str:
        params = self.default_params.copy()
        if custom_params:
            for k, v in custom_params.items():
                if k in params:
                    params[k] = v
        
        return (
            f"Hi there! Welcome to {params['store_name']}. It's a pretty busy morning! "
            f"What can I get started for you today?"
        )

    def validate_turn(self, user_input: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        params = self.default_params
        # 捕捉用户是否点了缺货的可颂
        if "croissant" in user_input.lower():
            return {
                "is_valid": True,
                "warning": f"小贴士：今天店里的可颂（{params['out_of_stock_item']}）已经售罄，收银员 Leo 会拒绝订单，您可以借此练习更换点单或取消商品的英语表达。",
                "modified_input": user_input
            }
            
        return {
            "is_valid": True,
            "warning": "",
            "modified_input": user_input
        }

    def get_evaluation_rules(self) -> str:
        return (
            "1. 评估用户是否能准确表述咖啡与餐饮的定制细节（如：加冰、脱脂奶、加热等）。\n"
            "2. 评估用户在面对商品售罄（可颂卖完）等突发情况时，能否流利应对并转换点单。\n"
            "3. 评估日常交易用语（如付款、打包带走、账单确认）的熟练度。"
        )
