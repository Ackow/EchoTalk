"""划词/划句解释服务：结合语境返回音标、中文释义与口语用法提示。"""
import json
import re

from app.agents.model_gateway import create_chat_model


async def explain_selection(text: str, context: str = "") -> dict:
    selected = (text or "").strip()
    ctx = (context or "").strip()
    if not selected:
        return {"text": "", "phonetic": "", "translation": "", "tip": ""}

    system_msg = (
        "You are a concise bilingual English-Chinese dictionary and speaking tutor. "
        "The learner highlighted an English word, phrase, or short sentence during a conversation. "
        "Return STRICT JSON only (no markdown fences):\n"
        '{"phonetic": "IPA phonetic transcription if it is a word or short phrase (e.g. /ˈaɪtɪnəreri/), or empty string for full sentences", '
        '"translation": "accurate Chinese meaning/translation in this context (include part of speech like n./v./adj. if it is a single word)", '
        '"tip": "1 short sentence in Chinese explaining pronunciation tips, collocation, or spoken nuance (optional)"}'
    )
    user_msg = f"Selected text: {selected}\nContext sentence: {ctx or '(none)'}"

    try:
        model = create_chat_model()
        ai_msg = await model.ainvoke([("system", system_msg), ("human", user_msg)])
        raw = ai_msg.content if isinstance(ai_msg.content, str) else str(ai_msg.content)
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)
        data = json.loads(cleaned)
        return {
            "text": selected,
            "phonetic": str(data.get("phonetic") or "").strip(),
            "translation": str(data.get("translation") or "").strip() or "暂无释义",
            "tip": str(data.get("tip") or "").strip(),
        }
    except Exception:
        return {
            "text": selected,
            "phonetic": "",
            "translation": "暂无法生成解释，可先点击右侧朗读听发音。",
            "tip": "",
        }
