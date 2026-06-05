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

def mock_llm_response(scene_id: str, user_text: str, rag_context: str = "") -> Dict[str, Any]:
    """
    未配置大模型 API Key 时的本地 Mock AI 角色对话及语法纠错生成器。
    根据不同的场景返回高度拟真且结合上下文/知识库的回复与纠错结果。
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
                reply = f"Interesting. Based on the reference documents, how would you handle {found_keyword} issues and optimize performance in React Native?"
            else:
                reply = "Understood. Let's look at the document requirements: how would you address potential API integration bottlenecks under heavy loads?"
        else:
            reply = "That sounds like a great start. Tell me about your experience with React Native and how you manage state in large-scale mobile apps."
        grammar_correction = {
            "original": user_text,
            "corrected": "I would like to practice speaking English for a developer job interview.",
            "explanation": "如果您说的是 practice English，这里微调为 practice speaking English 更加地道。"
        } if has_error else {
            "original": user_text,
            "corrected": user_text,
            "explanation": "没有发现明显的语法错误，表达很流利！"
        }
    elif "order" in scene_id_lower or "cafe" in scene_id_lower:
        if rag_context:
            keywords = ["latte", "espresso", "americano", "cappuccino", "bagel", "muffin", "croissant", "sandwich", "tea"]
            found_keyword = None
            for kw in keywords:
                if kw in rag_context.lower() or kw in user_text.lower():
                    found_keyword = kw
                    break
            if found_keyword:
                reply = f"Got it. A {found_keyword}. What size would you like for that, and do you want any milk or syrup with it?"
            else:
                reply = "Sure, I can get that started for you. Would you like any pastries, like a fresh croissant or muffin, to go with your drink?"
        else:
            reply = "Sure! A large vanilla latte and a slice of cheesecake. Would you like that hot or iced? And will that be for here or to go?"
        grammar_correction = {
            "original": user_text,
            "corrected": "Hello! I'd like to order a large vanilla latte and a slice of cheesecake.",
            "explanation": "口语表达中，使用 I'd like to 比 I want to 听起来更加礼貌得体。"
        } if has_error else {
            "original": user_text,
            "corrected": user_text,
            "explanation": "点餐用语符合规范，没有发现语法错误！"
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
                reply = f"Thanks for the update. Since you mentioned {found_keyword} is a critical factor, what specific support or resources do you need to speed things up?"
            else:
                reply = "I see. Based on our launch roadmap in the references, can we shift the QA timeline, or is the delay strictly on development?"
        else:
            reply = "I understand the status. How long do you think it will take to unblock the API integration, and can we get a revised estimation by today?"
        grammar_correction = {
            "original": user_text,
            "corrected": "I'd like to update you on the frontend progress and the blockers we face.",
            "explanation": "在同步会议中，使用 update you on progress 比 tell you the progress 听起来更加专业和本土化。"
        } if has_error else {
            "original": user_text,
            "corrected": user_text,
            "explanation": "表达简明扼要，语法正确，非常符合会议沟通习惯！"
        }
    else:
        # 针对任意未定义模版的自定义场景，尝试提取用户词汇，进行自适应模拟对话追问
        words = [w.strip(".,?!\"()") for w in user_text.split() if len(w) > 4 and w.lower() not in ["would", "about", "could", "there", "their", "where", "which"]]
        if words:
            key_term = words[-1]
            reply = f"I see. Since you mentioned '{key_term}', could you tell me more about how that fits into your practice scenario?"
        else:
            reply = f"I understand. Let's continue practicing. You said: '{user_text}'. What would you like to add next?"
        grammar_correction = {
            "original": user_text,
            "corrected": user_text,
            "explanation": "句子结构基本完整，未检测到重大语法硬伤。"
        }

    return {
        "reply": reply,
        "grammar_correction": grammar_correction
    }

async def generate_llm_response(
    scene_id: str,
    user_text: str,
    rag_context: str,
    conversation_history: list
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
        return mock_llm_response(scene_id, user_text, rag_context)

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
    instruction_prompt = (
        f"\n\n--- BUSINESS RULES ---\n"
        f"You must evaluate the user's latest input for grammatical correctness and naturalness. "
        f"Specific scene evaluation guidelines:\n{evaluation_rules}\n\n"
        f"CRITICAL: You must reply to the user as your assigned character AND output your analysis in a STRICT JSON format. "
        f"The JSON response must contain exactly the following structure:\n"
        f"{{\n"
        f'  "reply": "Your character\'s conversational response in English. Keep it natural, conversational, and relatively concise (1-3 sentences).",\n'
        f'  "grammar_correction": {{\n'
        f'    "original": "The user\'s original input text.",\n'
        f'    "corrected": "A corrected, polished version of the user\'s input. Keep it the same as original if no correction is needed.",\n'
        f'    "explanation": "A short, encouraging explanation of the corrections/improvements in Chinese. If there are no errors, output \'没有发现明显的语法错误，表达很棒！\'."\n'
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
        messages.append({
            "role": "system", 
            "content": (
                f"[Scene Reference Knowledge Base (PII Redacted)]:\n{rag_context}\n\n"
                f"As the interviewer, you must actively incorporate the above reference knowledge base "
                f"(which contains the candidate's background/resume, company product details, or specific technical criteria) "
                f"into your questions. Ask realistic, context-specific, and deep questions based on this knowledge base "
                f"rather than generic textbook questions. Challenge the candidate professionally as a real interviewer would."
            )
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
    # 百度短语音识别限制，同步阻塞运行
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

    # 5. 【步骤三】大模型隐私信息智能脱敏 (PII Redaction) - 并发执行
    user_pii_task = loop.run_in_executor(None, anonymize_text_via_llm, user_text_raw)
    if rag_raw_text:
        rag_pii_task = loop.run_in_executor(None, anonymize_text_via_llm, rag_raw_text)
        user_text_safe, rag_text_safe = await asyncio.gather(user_pii_task, rag_pii_task)
    else:
        user_text_safe = await user_pii_task
        rag_text_safe = ""

    # 6. 【步骤四】大模型角色演练回答 + 语法纠错
    llm_task = asyncio.create_task(generate_llm_response(
        scene_id=history.scene_id,
        user_text=user_text_safe,
        rag_context=rag_text_safe,
        conversation_history=history_turns_list
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

    # 调用 Edge-TTS 异步合成，不阻塞事件循环
    await async_text_to_speech(ai_reply_text, ai_audio_local_path)

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

    # 进行敏感信息过滤 - 并发执行
    user_pii_task = loop.run_in_executor(None, anonymize_text_via_llm, user_text_raw)
    if rag_raw_text:
        rag_pii_task = loop.run_in_executor(None, anonymize_text_via_llm, rag_raw_text)
        user_text_safe, rag_text_safe = await asyncio.gather(user_pii_task, rag_pii_task)
    else:
        user_text_safe = await user_pii_task
        rag_text_safe = ""

    # 5. 步骤三：开启大模型回复生成 (在此处直接 yield 'llm' 状态，使前端可以展示思考气泡，填补等待真空)
    yield {"status": "llm", "message": "AI 正在组织语言，撰写角色回复~"}

    llm_task = asyncio.create_task(generate_llm_response(
        scene_id=history.scene_id,
        user_text=user_text_safe,
        rag_context=rag_text_safe,
        conversation_history=history_turns_list
    ))

    # 等待大模型生成完成
    llm_result = await llm_task

    # 6. 步骤四：组织语言，合成 Edge-TTS 回复
    ai_reply_text = llm_result["reply"]
    ai_audio_filename = f"ai_reply_{history_id}_{int(time.time())}.mp3"
    
    temp_dir = settings.static_audio_dir
    os.makedirs(temp_dir, exist_ok=True)
    ai_audio_local_path = os.path.join(temp_dir, ai_audio_filename)

    # 异步合成 AI 语音
    await async_text_to_speech(ai_reply_text, ai_audio_local_path)

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
