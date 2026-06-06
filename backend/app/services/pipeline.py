import os
import time
import json
import asyncio
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from openai import OpenAI

from app.core.config import settings
from app.core.logger import log_api_call
from app.models import DialogueHistory, DialogueTurn
from app.services.stt import speech_to_text
from app.services.assessment import assess_pronunciation
from app.services.tts import text_to_speech, async_text_to_speech
from app.services.storage import upload_audio_to_kodo
from app.services.rag import query_scene_knowledge
from app.services.filter import anonymize_text_via_llm
from app.scenes.loader import get_scene

def clean_llm_json(text: str) -> str:
    """
    清理大模型返回的 JSON 字符串，剥离 Markdown 的 ```json 和 ``` 标记，防止解析异常。
    """
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def extract_item_from_text(user_text: str) -> Optional[str]:
    """
    从用户文本中提取可能的产品/项目名词（去除点餐常用语和停用词），以便在 Mock 对话中复用，增强拟真度。
    """
    text_lower = user_text.lower().strip()
    # 移除常见前缀
    for prefix in ["give me your", "give me", "i want to order", "i want", "i'd like to order", "i'd like", "could i have", "how about"]:
        if text_lower.startswith(prefix):
            text_lower = text_lower[len(prefix):].strip()
            break
            
    # 移除常见后缀
    for suffix in ["please", "how much", "how much is it", "all of them"]:
        if text_lower.endswith(suffix):
            text_lower = text_lower[:-len(suffix)].strip().rstrip(",;:")
            
    text_clean = text_lower.strip().rstrip("?.!")
    if len(text_clean) > 2:
        # 还原大小写：在原句中寻找该片段
        start_idx = user_text.lower().find(text_clean)
        if start_idx != -1:
            return user_text[start_idx:start_idx + len(text_clean)]
        return text_clean.title()
    return None


def dynamic_mock_correction(user_text: str, scene_type: str, speaking_style: str = "colloquial") -> Dict[str, str]:
    """
    根据用户输入的词汇和场景类型，动态生成基于原句修改的语法纠错（Mock 版），
    支持根据 speaking_style (colloquial vs formal) 切换修改的目标风格，
    避免直接替换为完全无关的硬编码句子，并保留用户提到的核心名词（如 chocolate Baker 等）。
    """
    text = user_text.strip().rstrip("?.!")
    text_lower = text.lower()

    corrections = []
    corrected = text

    # Cafe / Order scene
    if scene_type == "order" or scene_type == "cafe":
        if text_lower.startswith("give me"):
            rest = text[7:].strip()
            if rest.lower().endswith("how much"):
                items = rest[:-8].strip().rstrip(",;:")
                if speaking_style == "formal":
                    corrected = f"I would like to order the {items}. How much does it cost?"
                    corrections.append("建议将命令句 'give me' 替换为更正式的 'I would like to order'")
                    corrections.append("将口语简短问价 'how much' 规范化为 'How much does it cost?'")
                else:
                    corrected = f"Could I have {items}, please? How much is it?"
                    corrections.append("将直接的命令句 'give me' 改为更礼貌的请求 'Could I have ... please?'")
                    corrections.append("将句尾简短的 'how much' 规范化为完整的问句 'How much is it?'")
            else:
                if speaking_style == "formal":
                    corrected = f"I would like to order the {rest}, please."
                    corrections.append("建议将命令句 'give me' 替换为更正式的 'I would like to order'")
                else:
                    corrected = f"Could I have {rest}, please?"
                    corrections.append("将直接的命令句 'give me' 改为更礼貌的请求 'Could I have ... please?'")
        elif text_lower.startswith("i want"):
            rest = text[6:].strip()
            if rest.lower().endswith("how much"):
                items = rest[:-8].strip().rstrip(",;:")
                if speaking_style == "formal":
                    corrected = f"I would like to order the {items}. How much does it cost?"
                    corrections.append("将口语化的 'I want' 替换为更正式的 'I would like to order'")
                    corrections.append("将口语简短问价 'how much' 规范化为 'How much does it cost?'")
                else:
                    corrected = f"I would like to order {items}. How much is it?"
                    corrections.append("将口语化的 'I want' 优化为更得体的 'I would like to order'")
                    corrections.append("将句尾简短的 'how much' 规范化为完整的问句 'How much is it?'")
            else:
                if speaking_style == "formal":
                    corrected = f"I would like to order the {rest}."
                    corrections.append("将口语化的 'I want' 替换为更正式的 'I would like to order'")
                else:
                    corrected = f"I would like to order {rest}."
                    corrections.append("将口语化的 'I want' 优化为更得体的 'I would like to order'")
        else:
            if "how much" in text_lower:
                if text_lower.endswith("how much"):
                    main_part = text[:-8].strip().rstrip(",;:")
                    if speaking_style == "formal":
                        corrected = f"I would like to order the {main_part}. How much does it cost?"
                        corrections.append("使用正式句式并规范化价格询问为 'How much does it cost?'")
                    else:
                        corrected = f"I'd like to get {main_part}. How much is it?"
                        corrections.append("规范化问句中的价格询问方式")
                else:
                    corrected = text.replace("how much", "how much is it" if speaking_style != "formal" else "how much does it cost")
                    corrections.append("规范化价格询问表达")
            else:
                if speaking_style == "formal":
                    corrected = f"I would like to request: {text}."
                    corrections.append("在书面/正式表达中，添加 'I would like to request'")
                else:
                    corrected = f"I'd like to order: {text}."
                    corrections.append("在句首添加礼貌的点餐常用语 'I'd like to order'")

    # Interview scene
    elif scene_type == "interview":
        if "practice english" in text_lower:
            corrected = text.replace("practice english", "practice speaking English" if speaking_style != "formal" else "practice speaking the English language")
            corrections.append("优化 'practice English' 表达使其更符合英语母语习惯")
        elif text_lower.startswith("i want to"):
            corrected = "I would like to" + text[9:]
            corrections.append("建议将 'I want to' 替换为更正式的 'I would like to'")
        else:
            if speaking_style == "formal":
                corrected = f"I would like to state that {text[0].lower() + text[1:] if text else ''}"
                corrections.append("在正式面试中，使用 'I would like to state...' 显得更加沉稳专业")
            else:
                corrected = f"I would like to share that {text[0].lower() + text[1:] if text else ''}"
                corrections.append("在面试表达中，可以使用更自信和职业化的句式开头")

    # Meeting scene
    elif scene_type == "meeting":
        if "tell you" in text_lower:
            corrected = text.replace("tell you", "update you on" if speaking_style != "formal" else "present to you the update on")
            corrections.append("在工作会议中，替换 'tell you' 显得更加职业/正式")
        elif text_lower.startswith("i want"):
            corrected = ("I would like to " if speaking_style == "formal" else "I'd like to ") + text[6:].strip()
            corrections.append("建议将口语化的 'I want' 改为更适合会议汇报的表达")
        else:
            if speaking_style == "formal":
                corrected = f"I would like to inform the team that {text[0].lower() + text[1:] if text else ''}"
                corrections.append("在正式商务会议中，使用 'I would like to inform...' 显得格外正式庄重")
            else:
                corrected = f"I'd like to mention that {text[0].lower() + text[1:] if text else ''}"
                corrections.append("在同步会议中，使用 'I'd like to mention/state...' 会显得更加专业")

    # Fallback / General
    else:
        if text_lower.startswith("i want"):
            corrected = "I would like to " + text[6:].strip()
            corrections.append("使用 'I would like to' 比 'I want' 听起来更温和得体")
        else:
            corrected = text
            corrections.append("句式微调，使得体性更加符合设定的说话风格")

    # Capitalization and final punctuation
    if corrected:
        corrected = corrected.strip()
        corrected = corrected[0].upper() + corrected[1:]
        if not corrected.endswith((".", "?", "!")):
            if any(q in corrected.lower() for q in ["how", "what", "could", "would", "can", "is there"]):
                corrected += "?"
            else:
                corrected += "."

    explanation = f"语法建议（{ '书面化' if speaking_style == 'formal' else '口语化' }风格）：" + "；".join(corrections) + "。已保留您原本表达的核心内容。"
    
    grammar_sug = "；".join(corrections) if corrections else "您的语法表达非常棒，没有发现明显错误。"
    
    # Generate realistic vocabulary and pronunciation suggestions
    if scene_type in ["order", "cafe"]:
        vocab_sug = "在点餐场景中，可以尝试使用更礼貌客气的 'Could I please get...' 或 'I would like to order...' 替换命令式表达。"
        pron_sug = "朗读 'could I' 和 'get it' 时，注意辅音与元音的自然连读 (Liaison)，如 /kʊ.daɪ/ 和 /ɡe.dɪt/。"
    elif scene_type == "interview":
        vocab_sug = "在面试场景中，推荐使用 'I have extensive experience in...' 或 'I specialize in...' 来替换简单的 'I know...'，以显得更加专业自信。"
        pron_sug = "注意多音节词的重音位置，例如 'experience' 的重音在第二个音节 /ɪkˈspɪəriəns/，请避免平均用力。"
    elif scene_type == "meeting":
        vocab_sug = "在商务会议中，推荐使用 'Let me update you on...' 或 'Let's circle back to...' 替换普通的口语陈述，显得更为职业化。"
        pron_sug = "注意爆破音的失去爆破现象，如在 'update' 中，/p/ 发音时只做阻碍气流的口型，不产生爆破，直接过渡到 /d/。"
    else:
        vocab_sug = "日常口语中，多使用动词短语（Phrasal Verbs）如 'look forward to'、'check out' 等会使你的表达更加地道自然。"
        pron_sug = "朗读整句时注意意群（Sense Group）的划分，在连接词前稍微停顿，虚词（如 prep, pron）进行弱读。"

    return {
        "original": user_text,
        "corrected": corrected,
        "explanation": explanation,
        "suggestions": {
            "grammar": grammar_sug,
            "vocabulary": vocab_sug,
            "pronunciation": pron_sug
        }
    }


def mock_llm_response(scene_id: str, user_text: str, rag_context: str = "", speaking_style: str = "colloquial") -> Dict[str, Any]:
    """
    未配置大模型 API Key 时的本地 Mock AI 角色对话及语法纠错生成器。
    根据不同的场景以及所选择的 speaking_style (colloquial vs formal) 返回回复与纠错结果。
    """
    scene_id_lower = scene_id.lower()
    
    # 模拟语法纠错逻辑：如果包含 "icecola" 但拼写不对，或者故意设置些微纠错
    has_error = "icecola" in user_text.lower() or "hello" not in user_text.lower()
    
    if "interview" in scene_id_lower:
        if rag_context:
            keywords = ["performance", "optimization", "flatlist", "list", "memory", "image", "render", "state", "redux", "zustand"]
            found_keyword = None
            for kw in keywords:
                if kw in rag_context.lower() or kw in user_text.lower():
                    found_keyword = kw
                    break
            if found_keyword:
                if speaking_style == "formal":
                    reply = f"Thank you for sharing. According to our technical documentation, how would you address {found_keyword} concerns and ensure proper optimization in React Native?"
                else:
                    reply = f"Interesting. Based on the reference documents, how would you handle {found_keyword} issues and optimize performance in React Native?"
            else:
                reply = "Understood. Let's look at the document requirements: how would you address potential API integration bottlenecks under heavy loads?"
        else:
            if speaking_style == "formal":
                reply = "Thank you. Please describe your professional experience with React Native, specifically focusing on your state management strategies in enterprise mobile applications."
            else:
                reply = "That sounds like a great start. Tell me about your experience with React Native and how you manage state in large-scale mobile apps."
        
        grammar_correction = dynamic_mock_correction(user_text, "interview", speaking_style) if has_error else {
            "original": user_text,
            "corrected": user_text,
            "explanation": "没有发现明显的语法错误，表达很流利！",
            "suggestions": {
                "grammar": "没有语法错误，主谓一致，时态正确！",
                "vocabulary": "表达非常流畅。可以尝试使用如 'I would love to elaborate on...' 等短语替换基础句式以获得更好的印象分。",
                "pronunciation": "整体发音自然，注意句子重音在实词（名词、动词）上，弱读虚词。"
            }
        }
    elif "order" in scene_id_lower or "cafe" in scene_id_lower:
        item = extract_item_from_text(user_text)
        if item:
            if speaking_style == "formal":
                reply = f"Certainly. I shall prepare the {item} for you. May I inquire what size you would prefer, and would you like to consume it here or take it away?"
            else:
                reply = f"Sure! I can get the {item} started for you. What size would you like for that, and will that be for here or to go?"
        elif rag_context:
            keywords = ["latte", "espresso", "americano", "cappuccino", "bagel", "muffin", "croissant", "sandwich", "tea"]
            found_keyword = None
            for kw in keywords:
                if kw in rag_context.lower() or kw in user_text.lower():
                    found_keyword = kw
                    break
            if found_keyword:
                if speaking_style == "formal":
                    reply = f"Understood. A {found_keyword}. What is your preferred size, and would you care for any milk or syrup?"
                else:
                    reply = f"Got it. A {found_keyword}. What size would you like for that, and do you want any milk or syrup with it?"
            else:
                reply = "Sure, I can get that started for you. Would you like any pastries, like a fresh croissant or muffin, to go with your drink?"
        else:
            if speaking_style == "formal":
                reply = "Certainly. A large vanilla latte and a slice of cheesecake. Would you prefer it hot or iced, and is it for here or to go?"
            else:
                reply = "Sure! A large vanilla latte and a slice of cheesecake. Would you like that hot or iced? And will that be for here or to go?"
            
        grammar_correction = dynamic_mock_correction(user_text, "order", speaking_style) if has_error else {
            "original": user_text,
            "corrected": user_text,
            "explanation": "点餐用语符合规范，没有发现语法错误！",
            "suggestions": {
                "grammar": "点餐句式表达标准，单复数使用正确！",
                "vocabulary": "表达十分礼貌。在美式咖啡馆中，也可以用 'Can I grab a...?' 这种极其地道的常用口语词。",
                "pronunciation": "注意 'latte' 或 'croissant' 等外来词的母语标准发音，平时可多模仿朗读。"
            }
        }
    elif "meeting" in scene_id_lower:
        if rag_context:
            keywords = ["delay", "blocker", "estimation", "frontend", "api", "qa", "bug", "testing", "timeline"]
            found_keyword = None
            for kw in keywords:
                if kw in rag_context.lower() or kw in user_text.lower():
                    found_keyword = kw
                    break
            if found_keyword:
                if speaking_style == "formal":
                    reply = f"Thank you for the update. Since you have identified {found_keyword} as a critical factor, what specific support or resources do you require to accelerate the timeline?"
                else:
                    reply = f"Thanks for the update. Since you mentioned {found_keyword} is a critical factor, what specific support or resources do you need to speed things up?"
            else:
                reply = "I see. Based on our launch roadmap in the references, can we shift the QA timeline, or is the delay strictly on development?"
        else:
            if speaking_style == "formal":
                reply = "I acknowledge the status. Could you provide a timeline for unblocking the API integration, and can we obtain a revised estimation by the end of today?"
            else:
                reply = "I understand the status. How long do you think it will take to unblock the API integration, and can we get a revised estimation by today?"
            
        grammar_correction = dynamic_mock_correction(user_text, "meeting", speaking_style) if has_error else {
            "original": user_text,
            "corrected": user_text,
            "explanation": "表达简明扼要，语法正确，非常符合会议沟通习惯！",
            "suggestions": {
                "grammar": "时态和主谓关系正确，句子结构清晰明了！",
                "vocabulary": "商务会议表达很职业。也可以使用诸如 'I'd like to pitch in on...' 来表示自己想补充说明某事。",
                "pronunciation": "整体语流连贯。在快速陈述时，注意 'and' 或 'but' 等连接词的弱读，使得语调更有节奏感。"
            }
        }
    else:
        words = [w.strip(".,?!\"()") for w in user_text.split() if len(w) > 4 and w.lower() not in ["would", "about", "could", "there", "their", "where", "which"]]
        if words:
            key_term = words[-1]
            reply = f"I see. Since you mentioned '{key_term}', could you tell me more about how that fits into your practice scenario?"
        else:
            reply = f"I understand. Let's continue practicing. You said: '{user_text}'. What would you like to add next?"
            
        grammar_correction = dynamic_mock_correction(user_text, "general", speaking_style)

    return {
        "reply": reply,
        "grammar_correction": grammar_correction
    }

async def generate_llm_response(
    scene_id: str,
    user_text: str,
    rag_context: str,
    conversation_history: list,
    speaking_style: str = "colloquial"
) -> Dict[str, Any]:
    """
    根据场景设置、前序历史、RAG 召回块以及脱敏后的用户文本，调用大语言模型。
    要求模型严格输出包含 AI 回复 (reply) 和语法纠错 (grammar_correction) 的 JSON。
    自适应调用 DeepSeek、Xiaomi MiMo 或 OpenAI，未配置时自动降级到本地 Mock 引擎。
    """
    # 1. 确定调用凭证
    api_key = None
    base_url = None
    model_name = None
    provider_name = ""
    
    if settings.DEEPSEEK_API_KEY:
        api_key = settings.DEEPSEEK_API_KEY
        base_url = settings.DEEPSEEK_BASE_URL
        model_name = settings.DEEPSEEK_MODEL
        provider_name = "DeepSeek"
    elif settings.XIAOMI_API_KEY:
        api_key = settings.XIAOMI_API_KEY
        base_url = settings.XIAOMI_BASE_URL
        model_name = settings.XIAOMI_MODEL
        provider_name = "Xiaomi MiMo"
    elif settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "mock-key":
        api_key = settings.OPENAI_API_KEY
        base_url = settings.OPENAI_BASE_URL
        model_name = settings.OPENAI_MODEL
        provider_name = "OpenAI"

    has_credentials = bool(api_key)

    if not has_credentials:
        log_api_call(
            api_type="大语言模型 (LLM)",
            provider="本地离线引擎",
            url="None (Offline)",
            model="None",
            action="生成角色回复与语法纠错 (generate_llm_response)",
            status="success",
            extra_info="未配置大模型 Key，自动降级至 Mock 角色对话生成器。"
        )
        return mock_llm_response(scene_id, user_text, rag_context, speaking_style)

    # 2. 从加载器获取场景 System Prompt
    # 临时建一个内存 db 查询，如果不可用直接用静态缓存
    scene_obj = get_scene(scene_id)
    if scene_obj:
        system_prompt = scene_obj.get_system_prompt()
        evaluation_rules = scene_obj.get_evaluation_rules()
    else:
        system_prompt = "You are a friendly English conversation partner."
        evaluation_rules = "请针对用户的语法准确性进行评价。"

    # 3. 构造大模型 Prompt 和 JSON Schema 约束
    style_guidelines = ""
    if speaking_style == "formal":
        style_guidelines = (
            "STYLE - FORMAL/WRITTEN ENGLISH:\n"
            "1. You must respond in a formal, professional, and grammatically standard written English style. Avoid casual slang, abbreviations (e.g. use 'do not' instead of 'don't' where appropriate for maximum formality, though standard contractions are allowed if they fit the role), and filler words.\n"
            "2. Keep the responses well-structured and polite. If the scene is an interview, behave as a formal interviewer. If the scene is cafe ordering, behave as a polite, standard barista.\n"
            "3. For 'grammar_correction' -> 'corrected', correct the user's grammar to make it sound formal, professional, and grammatically impeccable, while preserving original items/nouns."
        )
    else:  # colloquial (default)
        style_guidelines = (
            "STYLE - COLLOQUIAL/SPOKEN ENGLISH:\n"
            "1. You must respond in a natural, colloquial spoken English style. Actively use contractions (e.g. I'm, I'd, we've, don't, gonna, wanna) and occasional natural spoken filler words (e.g. 'Well, ...', 'Actually, ...', 'You know, ...', 'So, ...').\n"
            "2. Keep replies concise, mimicking real face-to-face spoken conversation (1-2 sentences). Avoid long lecturing paragraphs.\n"
            "3. Practice active listening: acknowledge the user's response briefly (e.g., 'Oh, that's interesting!', 'Got it.', 'Okay, cool.') before asking follow-up questions.\n"
            "4. Incorporate scene-specific spoken vocabulary:\n"
            "   - If this is a Cafe scene, use barista phrasings like 'What can I get started for you today?', 'Any room for cream?', 'For here or to go?'.\n"
            "   - If this is a Business Meeting scene, use coworker idioms like 'touch base', 'circle back', 'loop in', 'blocker', 'keep me posted'.\n"
            "5. For 'grammar_correction' -> 'corrected', make corrections that sound natural, polite, and fluent in daily spoken conversation rather than overly academic or textbook-like."
        )

    instruction_prompt = (
        f"\n\n--- BUSINESS RULES ---\n"
        f"You must evaluate the user's latest input for grammatical correctness and naturalness. "
        f"Specific scene evaluation guidelines:\n{evaluation_rules}\n\n"
        f"CRITICAL: You must reply to the user as your assigned character AND output your analysis in a STRICT JSON format.\n"
        f"CRITICAL GRAMMAR CORRECTION RULES:\n"
        f"1. In 'grammar_correction' -> 'corrected', you MUST keep the user's original meaning, core vocabulary, and specific items (e.g., if the user said 'chocolate Baker', keep 'chocolate Baker' or slightly fix it to 'chocolate babka' / 'chocolate bakery items' if it is a typo, but DO NOT replace it with 'vanilla latte' or other unrelated food/drink). Do not fabricate completely new requests.\n"
        f"2. Make corrections on top of the user's original sentence structure rather than rewriting it from scratch into a different scenario.\n\n"
        f"{style_guidelines}\n\n"
        f"The JSON response must contain exactly the following structure:\n"
        f"{{\n"
        f'  "reply": "Your character\'s conversational response in English. Keep it natural, conversational, and relatively concise (1-3 sentences).",\n'
        f'  "grammar_correction": {{\n'
        f'    "original": "The user\'s original input text.",\n'
        f'    "corrected": "A corrected, polished version of the user\'s input. Keep it the same as original if no correction is needed.",\n'
        f'    "explanation": "A short, encouraging explanation of the corrections/improvements in Chinese. If there are no errors, output \'没有发现明显的语法错误，表达很棒！\'.",\n'
        f'    "suggestions": {{\n'
        f'      "grammar": "有关语法错误的解释与改进剖析（中文），若无语法错误请简述并肯定用户。",\n'
        f'      "vocabulary": "地道词汇或表达升级推荐（中文），如何表达更生动，可附带地道例句。",\n'
        f'      "pronunciation": "针对这句英文的连读（liaison）、失去爆破（loss of explosion）或重音易错点给出针对性的口语语音指导提示（中文）。"\n'
        f'    }}\n'
        f'  }}\n'
        f"}}\n"
        f"Do not include any other text, prefix, suffix, or markdown tags outside the JSON block. Do not output ```json or ``` code block wrappers."
    )

    # 4. 构造完整消息队列
    messages = [
        {"role": "system", "content": system_prompt + instruction_prompt}
    ]

    # 添加 RAG 背景库知识（如果有的话）
    if rag_context:
        # Determine the role for the RAG instruction based on system prompt
        system_prompt_lower = system_prompt.lower()
        if "barista" in system_prompt_lower or "cafe" in system_prompt_lower or "cashier" in system_prompt_lower:
            role_description = "barista/cashier"
            ref_description = "cafe menu and customer service manual"
        elif "interviewer" in system_prompt_lower or "interview" in system_prompt_lower:
            role_description = "interviewer"
            ref_description = "candidate's background/resume, company product details, or specific technical criteria"
        elif "manager" in system_prompt_lower or "meeting" in system_prompt_lower or "chairperson" in system_prompt_lower:
            role_description = "chairperson or colleague"
            ref_description = "meeting notes, project requirements, schedules, or technical data"
        else:
            role_description = "practice partner"
            ref_description = "reference knowledge base"

        # Check if RAG context has money/pricing content to dynamically enforce pricing constraint
        has_pricing_content = (
            "$" in rag_context 
            or "¥" in rag_context 
            or "元" in rag_context 
            or "price" in rag_context.lower() 
            or "cost" in rag_context.lower() 
            or "fee" in rag_context.lower()
            or "charge" in rag_context.lower()
            or "menu" in rag_context.lower()
            or "billing" in rag_context.lower()
        )

        pricing_instruction = ""
        if has_pricing_content:
            pricing_instruction = (
                f"CRITICAL PRICE CONSTRAINT (STRICT ENFORCEMENT):\n"
                f"1. When the user asks for the bill, checkout, or total price of items/services, you MUST calculate the total price mathematically and strictly according to the exact prices, fees, and surcharges listed in the reference knowledge base.\n"
                f"2. Check for item options, sizes, and customizations. Add any premium alternatives or surcharges precisely.\n"
                f"3. You MUST sum up these values mathematically to get the exact total. DO NOT estimate, hallucinate, or make up prices or totals under any circumstances (e.g. if the item is $4.25 and customization is free/no charge, the total is exactly $4.25, NOT $4.50 or any other estimated amount).\n"
                f"4. If any items or services ordered are specified as out-of-stock or unavailable in the reference, apologize politely and suggest a listed alternative.\n\n"
            )

        rag_content = (
            f"[Scene Reference Knowledge Base (PII Redacted)]:\n{rag_context}\n\n"
            f"As the {role_description}, you must actively incorporate the above {ref_description} "
            f"into your responses. Be context-specific, professional, and realistic based on this knowledge base rather than asking generic questions.\n\n"
            f"{pricing_instruction}"
        )

        messages.append({
            "role": "system", 
            "content": rag_content
        })

    # 添加历史对话轮次
    for turn in conversation_history:
        messages.append({"role": turn["role"], "content": turn["text"]})

    # 追加当前输入
    messages.append({"role": "user", "content": user_text})

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        log_api_call(
            api_type="大语言模型 (LLM)",
            provider=provider_name,
            url=base_url,
            model=model_name,
            action="生成角色回复与语法纠错 (generate_llm_response)",
            status="pending"
        )

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
            max_tokens=800,
            response_format={"type": "json_object"} if provider_name != "Xiaomi MiMo" else None # 小米可能不完全支持 json_object 参数，做安全过滤
        )
        
        raw_content = response.choices[0].message.content
        if not raw_content:
            raise Exception("大模型接口返回了空文本")
            
        clean_content = clean_llm_json(raw_content)
        parsed_json = json.loads(clean_content)
        
        # 字段完整性防御校验
        if "reply" not in parsed_json or "grammar_correction" not in parsed_json:
            raise KeyError("JSON 中缺失 required 字段 reply 或 grammar_correction")
            
        log_api_call(
            api_type="大语言模型 (LLM)",
            provider=provider_name,
            url=base_url,
            model=model_name,
            action="生成角色回复与语法纠错 (generate_llm_response)",
            status="success",
            extra_info=f"AI 回复前 30 字: '{parsed_json['reply'][:30]}...'"
        )
        return parsed_json

    except Exception as e:
        log_api_call(
            api_type="大语言模型 (LLM)",
            provider=provider_name,
            url=base_url,
            model=model_name,
            action="生成角色回复与语法纠错 (generate_llm_response)",
            status="failed",
            extra_info=f"调用大模型或 JSON 解析失败: {str(e)}。已安全降级至 Mock 角色生成器。"
        )
        # 出错降级
        return mock_llm_response(scene_id, user_text, rag_context)


async def run_dialogue_turn_pipeline(
    db: Session,
    history_id: int,
    user_audio_path: str
) -> Tuple[DialogueTurn, DialogueTurn]:
    """
    对话管道核心控制器。
    接收当前会话 ID 和用户录音本地路径，串联 STT -> RAG 检索 -> PII 脱敏 -> 并行执行(发音测评 + LLM 对话/纠错) -> TTS -> 资源上传托管 -> 数据持久化全生命周期。
    返回数据库创建 of (user_turn_model_instance, assistant_turn_model_instance) 二元组。
    """
    log_api_call(
        api_type="管道流程编排 (Pipeline)",
        provider="EchoTalk Orchestrator",
        url="N/A",
        model="N/A",
        action="执行口语对话 Pipeline (run_dialogue_turn_pipeline)",
        status="pending",
        extra_info=f"会话 ID: {history_id}, 待评估音频: '{user_audio_path}'"
    )

    # 1. 检验会话记录是否存在
    history = db.query(DialogueHistory).filter(DialogueHistory.id == history_id).first()
    if not history:
        raise ValueError(f"指定会话历史记录 ID {history_id} 不存在")

    loop = asyncio.get_running_loop()

    # 0. 【并行上传任务预热】提前开始上传用户原始音频至七牛云/本地托管
    user_audio_filename = f"user_voice_{history_id}_{int(time.time())}.wav"
    upload_user_task = loop.run_in_executor(None, upload_audio_to_kodo, user_audio_path, user_audio_filename)

    # 2. 【步骤一】语音转文字 (STT) 识别出用户原声
    # 腾讯云极速语音识别 (Flash ASR)，同步阻塞运行
    user_text_raw = speech_to_text(user_audio_path)

    # 【并发启动】科大讯飞流式发音评测 (传入原始音频和 ASR 识别结果)，不等待 RAG/PII 脱敏直接触发
    assessment_task = asyncio.create_task(assess_pronunciation(user_audio_path, user_text_raw))
    
    # 3. 提取对话历史结构供大模型上下文理解
    turns_db = db.query(DialogueTurn).filter(
        DialogueTurn.dialogue_history_id == history_id
    ).order_by(DialogueTurn.timestamp.asc()).all()
    
    history_turns_list = []
    for t in turns_db:
        history_turns_list.append({
            "role": "user" if t.role == "user" else "assistant",
            "text": t.text
        })

    # 4. 【步骤二】RAG 检索相关文档库分块
    matched_chunks = query_scene_knowledge(history.scene_id, user_text_raw, top_k=2)
    rag_raw_text = "\n".join(matched_chunks) if matched_chunks else ""

    # 5. 【步骤三】大模型隐私信息智能脱敏 (PII Redaction)
    # 仅对用户动态输入的内容进行脱敏，知识库属于静态参考文本，无需脱敏以省去大量的 API 请求时间
    user_text_safe = await loop.run_in_executor(None, anonymize_text_via_llm, user_text_raw)
    rag_text_safe = rag_raw_text

    # 6. 【步骤四】大模型角色演练回答 + 语法纠错
    llm_task = asyncio.create_task(generate_llm_response(
        scene_id=history.scene_id,
        user_text=user_text_safe,
        rag_context=rag_text_safe,
        conversation_history=history_turns_list,
        speaking_style=getattr(history, "speaking_style", "colloquial")
    ))

    # 等待大模型生成完成，以便开始 TTS
    llm_result = await llm_task

    # 7. 【步骤五】AI 文本转语音合成 (TTS) 并保存至本地临时目录
    ai_reply_text = llm_result["reply"]
    ai_audio_filename = f"ai_reply_{history_id}_{int(time.time())}.mp3"
    
    # 确定临时存储和托管静态文件目录
    temp_dir = settings.static_audio_dir
    os.makedirs(temp_dir, exist_ok=True)
    ai_audio_local_path = os.path.join(temp_dir, ai_audio_filename)

    # 提取口音并映射为对应的发音人音色
    accent = getattr(history, "accent", "us")
    voice = "en-GB-SoniaNeural" if accent == "uk" else "en-US-EmmaMultilingualNeural"
    # 调用 Edge-TTS/腾讯云 异步合成，不阻塞事件循环
    await async_text_to_speech(ai_reply_text, ai_audio_local_path, voice=voice)

    # 8. 【步骤六】开始并发上传 AI 音频文件
    upload_ai_task = loop.run_in_executor(None, upload_audio_to_kodo, ai_audio_local_path, ai_audio_filename)
    
    # 统一收拢并发任务：口音评测、用户音频上传、AI音频上传
    pronunciation_result, user_audio_url, ai_audio_url = await asyncio.gather(
        assessment_task,
        upload_user_task,
        upload_ai_task
    )

    # 9. 【步骤七】数据持久化与数据库事务提交
    # (1) 创建用户对话轮次纪录
    user_turn = DialogueTurn(
        dialogue_history_id=history_id,
        role="user",
        text=user_text_raw,
        audio_url=user_audio_url,
        pronunciation_score=pronunciation_result,
        grammar_correction=llm_result["grammar_correction"]
    )
    # (2) 创建 AI 助手回复轮次纪录
    assistant_turn = DialogueTurn(
        dialogue_history_id=history_id,
        role="assistant",
        text=ai_reply_text,
        audio_url=ai_audio_url,
        audio_url_us=ai_audio_url if accent == "us" else None,
        audio_url_uk=ai_audio_url if accent == "uk" else None,
        pronunciation_score=None,
        grammar_correction=None
    )

    db.add(user_turn)
    db.add(assistant_turn)
    db.commit()
    db.refresh(user_turn)
    db.refresh(assistant_turn)

    log_api_call(
        api_type="管道流程编排 (Pipeline)",
        provider="EchoTalk Orchestrator",
        url="N/A",
        model="N/A",
        action="执行口语对话 Pipeline (run_dialogue_turn_pipeline)",
        status="success",
        extra_info=f"Pipeline 顺利跑通。用户识别: '{user_text_raw[:20]}...'，AI回复: '{ai_reply_text[:20]}...'"
    )

    return user_turn, assistant_turn


async def run_dialogue_turn_pipeline_stream(
    db: Session,
    history_id: int,
    user_audio_path: str
):
    """
    对话管道流式状态推送控制器。
    分步执行 STT -> RAG -> 脱敏 -> ISE & LLM -> TTS -> Upload -> Save，并向外 yield 当前的进度与识别数据。
    """
    log_api_call(
        api_type="流式管道流程编排 (Pipeline Stream)",
        provider="EchoTalk Orchestrator",
        url="N/A",
        model="N/A",
        action="执行口语对话流式 Pipeline (run_dialogue_turn_pipeline_stream)",
        status="pending",
        extra_info=f"会话 ID: {history_id}, 待评估音频: '{user_audio_path}'"
    )

    # 1. 验证会话是否存在
    history = db.query(DialogueHistory).filter(DialogueHistory.id == history_id).first()
    if not history:
        raise ValueError(f"指定会话历史记录 ID {history_id} 不存在")

    loop = asyncio.get_running_loop()

    # 0. 【并行上传任务预热】提前开始上传用户原始音频至七牛云/本地托管
    user_audio_filename = f"user_voice_{history_id}_{int(time.time())}.wav"
    upload_user_task = loop.run_in_executor(None, upload_audio_to_kodo, user_audio_path, user_audio_filename)

    # 2. 步骤一：开始语音转文字
    yield {"status": "asr", "message": "正在认真聆听您说了什么~"}

    # 执行语音转文字 (ASR)
    user_text_raw = speech_to_text(user_audio_path)

    # 3. 步骤一完成：发送识别文字
    yield {"status": "asr_done", "text": user_text_raw}

    # 【并发启动】开启口语发音评测，不等待 RAG/PII 脱敏直接触发
    assessment_task = asyncio.create_task(assess_pronunciation(user_audio_path, user_text_raw))

    # 4. 步骤二：开启隐私脱敏与 RAG 检索
    yield {"status": "ise", "message": "正在检测您的口音，分析发音表现~"}
    yield {"status": "pii", "message": "正在保护您的隐私，脱敏处理中~"}

    # 提取历史对话
    turns_db = db.query(DialogueTurn).filter(
        DialogueTurn.dialogue_history_id == history_id
    ).order_by(DialogueTurn.timestamp.asc()).all()
    
    history_turns_list = []
    for t in turns_db:
        history_turns_list.append({
            "role": "user" if t.role == "user" else "assistant",
            "text": t.text
        })

    # 检索匹配 RAG 分块
    matched_chunks = query_scene_knowledge(history.scene_id, user_text_raw, top_k=2)
    rag_raw_text = "\n".join(matched_chunks) if matched_chunks else ""

    # 进行敏感信息过滤
    # 仅对用户动态输入的内容进行脱敏，知识库属于静态参考文本，无需脱敏以省去大量的 API 请求时间
    user_text_safe = await loop.run_in_executor(None, anonymize_text_via_llm, user_text_raw)
    rag_text_safe = rag_raw_text

    # 5. 步骤三：开启大模型回复生成 (在此处直接 yield 'llm' 状态，使前端可以展示思考气泡，填补等待真空)
    yield {"status": "llm", "message": "AI 正在组织语言，撰写角色回复~"}

    llm_task = asyncio.create_task(generate_llm_response(
        scene_id=history.scene_id,
        user_text=user_text_safe,
        rag_context=rag_text_safe,
        conversation_history=history_turns_list,
        speaking_style=getattr(history, "speaking_style", "colloquial")
    ))

    # 等待大模型生成完成
    llm_result = await llm_task

    # 6. 步骤四：组织语言，合成 Edge-TTS 回复
    ai_reply_text = llm_result["reply"]
    ai_audio_filename = f"ai_reply_{history_id}_{int(time.time())}.mp3"
    
    temp_dir = settings.static_audio_dir
    os.makedirs(temp_dir, exist_ok=True)
    ai_audio_local_path = os.path.join(temp_dir, ai_audio_filename)

    # 提取口音并映射为对应的发音人音色
    accent = getattr(history, "accent", "us")
    voice = "en-GB-SoniaNeural" if accent == "uk" else "en-US-EmmaMultilingualNeural"
    # 异步合成 AI 语音
    await async_text_to_speech(ai_reply_text, ai_audio_local_path, voice=voice)

    # 并行上传 AI 录音
    upload_ai_task = loop.run_in_executor(None, upload_audio_to_kodo, ai_audio_local_path, ai_audio_filename)
    
    # 统一收拢并发任务：口音评测、用户音频上传、AI音频上传
    pronunciation_result, user_audio_url, ai_audio_url = await asyncio.gather(
        assessment_task,
        upload_user_task,
        upload_ai_task
    )

    # 7. 步骤五：数据库持久化写入
    user_turn = DialogueTurn(
        dialogue_history_id=history_id,
        role="user",
        text=user_text_raw,
        audio_url=user_audio_url,
        pronunciation_score=pronunciation_result,
        grammar_correction=llm_result["grammar_correction"]
    )
    assistant_turn = DialogueTurn(
        dialogue_history_id=history_id,
        role="assistant",
        text=ai_reply_text,
        audio_url=ai_audio_url,
        audio_url_us=ai_audio_url if accent == "us" else None,
        audio_url_uk=ai_audio_url if accent == "uk" else None,
        pronunciation_score=None,
        grammar_correction=None
    )

    db.add(user_turn)
    db.add(assistant_turn)
    db.commit()
    db.refresh(user_turn)
    db.refresh(assistant_turn)

    # 序列化结果以防 ORM 对象脱离 session 导致报错
    user_data = {
        "id": user_turn.id,
        "dialogue_history_id": user_turn.dialogue_history_id,
        "role": user_turn.role,
        "text": user_turn.text,
        "audio_url": user_turn.audio_url,
        "pronunciation_score": user_turn.pronunciation_score,
        "grammar_correction": user_turn.grammar_correction,
        "timestamp": user_turn.timestamp.isoformat() if user_turn.timestamp else None
    }
    ai_data = {
        "id": assistant_turn.id,
        "dialogue_history_id": assistant_turn.dialogue_history_id,
        "role": assistant_turn.role,
        "text": assistant_turn.text,
        "audio_url": assistant_turn.audio_url,
        "pronunciation_score": assistant_turn.pronunciation_score,
        "grammar_correction": assistant_turn.grammar_correction,
        "timestamp": assistant_turn.timestamp.isoformat() if assistant_turn.timestamp else None
    }

    log_api_call(
        api_type="流式管道流程编排 (Pipeline Stream)",
        provider="EchoTalk Orchestrator",
        url="N/A",
        model="N/A",
        action="执行口语对话流式 Pipeline (run_dialogue_turn_pipeline_stream)",
        status="success",
        extra_info=f"Pipeline 流式模式顺利通关。会话ID: {history_id}"
    )

    # 8. 发送完成状态及结果
    yield {"status": "done", "result": [user_data, ai_data]}
