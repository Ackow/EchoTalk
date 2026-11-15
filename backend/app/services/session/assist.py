"""练习会话 AI 回复建议（结合当前阶段、目标与学习者可见资料）。"""
from copy import deepcopy
import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.model_gateway import create_chat_model
from app.core.errors import AppError
from app.models import Chunk, Document, PracticeTurn
from app.scenes.registry import validate
from app.services.session.crud import owned_session

logger = logging.getLogger("echotalk")


async def suggest_reply(db: Session, user_id: int, session_id: str) -> dict:
    """结合当前场景阶段、目标与最近对话，生成 2~3 条地道英语参考回复。"""
    row = owned_session(db, session_id, user_id)
    if row.state_json.get("status") != "active":
        raise AppError("本次练习已结束", code="SESSION_FINISHED", status_code=409)
    package = validate(deepcopy(row.scene_snapshot))
    state, greeting = deepcopy(row.state_json), row.greeting
    recent = list(
        reversed(
            db.scalars(
                select(PracticeTurn)
                .where(PracticeTurn.session_id == session_id)
                .order_by(PracticeTurn.number.desc())
                .limit(6)
            ).all()
        )
    )
    pkg_ai_only = {f.path for f in package.knowledge.files if f.visibility == "ai_only"}
    user_visible_files = {f.path for f in package.knowledge.files if f.visibility == "user"}
    db_user_docs = db.scalars(
        select(Document.filename).where(Document.scene_id == package.meta.id, Document.visibility == "user")
    ).all()
    user_visible_files.update(name for name in db_user_docs if name not in pkg_ai_only)
    kb_snippets: list[str] = []
    if user_visible_files:
        from app.scenes.retrieval import search_scene

        last_partner = recent[-1].response_json.get("text", "") if recent else greeting
        kb_query = f"{package.meta.name} {last_partner}".strip()[:200]
        try:
            hits = search_scene(db, package.meta.id, kb_query, top_k=5).get("items") or []
            for item in hits:
                fname = item.get("filename") or ""
                if fname in user_visible_files and item.get("text"):
                    kb_snippets.append(f"[{fname}] {item['text']}")
        except Exception:
            pass
        if not kb_snippets:
            rows = db.scalars(
                select(Chunk)
                .join(Document, Chunk.doc_id == Document.id)
                .where(Chunk.scene_id == package.meta.id, Document.filename.in_(user_visible_files))
                .order_by(Chunk.chunk_index.asc())
                .limit(3)
            ).all()
            kb_snippets = [c.text for c in rows if c.text]
    db.rollback()

    stage_id = state.get("stage")
    stage = next((s for s in package.stages if s.id == stage_id), None)
    stage_desc = f"{stage.name}: {stage.guidance}" if stage and stage.guidance else (stage.name if stage else "")
    pending_goals = [g["label"] for g in state.get("goals", []) if not g.get("done")][:3]

    history_lines = []
    if greeting:
        history_lines.append(f"Partner: {greeting}")
    for t in recent:
        history_lines.append(f"Learner: {t.input_text}")
        history_lines.append(f"Partner: {t.response_json.get('text', '')}")

    system_msg = (
        "You are an English speaking coach inside EchoTalk. "
        "Suggest 3 short, natural, spoken English replies the learner can say next in this roleplay. "
        "Keep each reply concise (1-2 sentences) and suited to the current stage and goals. "
        "If reference material is provided, ONLY suggest items/options/facts that appear in it. "
        'Return strict JSON only: {"suggestions": [{"en": "...", "zh": "简短中文意思"}, ...]}.'
    )
    kb_block = ("\n\nReference material (visible to learner):\n" + "\n---\n".join(kb_snippets[:3])) if kb_snippets else ""
    user_msg = (
        f"Scenario: {package.meta.name} ({package.meta.description})\n"
        f"Current stage: {stage_desc}\n"
        f"Pending goals: {', '.join(pending_goals) if pending_goals else 'Continue natural conversation'}"
        f"{kb_block}\n\n"
        "Recent dialogue:\n"
        + ("\n".join(history_lines) if history_lines else "(Just started)")
    )

    def _extract_text(msg) -> str:
        content = getattr(msg, "content", msg)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict) and block.get("text"):
                    parts.append(str(block["text"]))
            return "\n".join(parts)
        return str(content or "")

    def _parse_suggestions(raw_text: str) -> list[dict[str, str]]:
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_text, flags=re.IGNORECASE)
        cleaned = re.sub(r"<think>[\s\S]*$", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE).strip()

        obj_idx = cleaned.find("{")
        arr_idx = cleaned.find("[")
        json_candidate = cleaned
        if arr_idx != -1 and (obj_idx == -1 or arr_idx < obj_idx):
            m = re.search(r"\[[\s\S]*\]", cleaned)
            if m:
                json_candidate = m.group(0)
        elif obj_idx != -1:
            m = re.search(r"\{[\s\S]*\}", cleaned)
            if m:
                json_candidate = m.group(0)

        parsed_list: list[dict[str, str]] = []
        try:
            parsed = json.loads(json_candidate)
            items = parsed.get("suggestions") if isinstance(parsed, dict) else parsed
            if isinstance(items, list):
                for item in items[:3]:
                    if isinstance(item, dict) and str(item.get("en", "")).strip():
                        parsed_list.append({
                            "en": str(item["en"]).strip(),
                            "zh": str(item.get("zh", "")).strip(),
                        })
                    elif isinstance(item, str) and item.strip():
                        parsed_list.append({"en": item.strip(), "zh": ""})
        except Exception:
            pass

        if not parsed_list and cleaned:
            en_matches = re.findall(r'"en"\s*:\s*"([^"]+)"', cleaned)
            zh_matches = re.findall(r'"zh"\s*:\s*"([^"]*)"', cleaned)
            if en_matches:
                for idx, en_txt in enumerate(en_matches[:3]):
                    if en_txt.strip():
                        parsed_list.append({
                            "en": en_txt.strip(),
                            "zh": zh_matches[idx].strip() if idx < len(zh_matches) else "",
                        })
        if not parsed_list and cleaned:
            lines = [
                ln.strip("-• 1234567890.")
                for ln in cleaned.splitlines()
                if ln.strip() and not ln.strip().startswith(("{", "}", "[", "]", '"suggestions"'))
            ]
            parsed_list = [{"en": ln, "zh": ""} for ln in lines[:3] if ln]
        return parsed_list

    model = create_chat_model()
    suggestions: list[dict[str, str]] = []
    last_raw = ""
    for attempt in range(2):
        prompt_user = user_msg if attempt == 0 else (
            f"Scenario: {package.meta.name}\n"
            f"Last partner line: {greeting if not recent else recent[-1].response_json.get('text', '')}\n"
            'Give 3 short spoken English replies the learner can say next. Return JSON: {"suggestions": [{"en": "...", "zh": "..."}]}'
        )
        ai_msg = await model.ainvoke([("system", system_msg), ("human", prompt_user)])
        last_raw = _extract_text(ai_msg)
        suggestions = _parse_suggestions(last_raw)
        if suggestions:
            break
    if not suggestions:
        logger.warning("suggest_reply empty after retries; last_raw=%r", last_raw[:400])
        raise AppError("AI 暂未生成有效参考回复，请重试", code="SUGGEST_REPLY_EMPTY", status_code=502)
    return {"suggestions": suggestions}
