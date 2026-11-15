"""复习计划服务：从对话记录提取薄弱点、SM-2 间隔重复调度与持久化。"""
from datetime import datetime, timedelta
import hashlib

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.timeutil import utcnow
from app.models.practice import PracticeSession, PracticeTurn
from app.models.review import ReviewItem
from app.schemas.review import ReviewItemCreate, ReviewItemUpdate, ReviewRating
from app.services.listening_service import award_xp

_TABLE_READY = False


def ensure_review_table(db: Session) -> None:
    """首次访问时幂等建表，避免未重跑 init_db.py 时报错。"""
    global _TABLE_READY
    if _TABLE_READY:
        return
    ReviewItem.__table__.create(bind=db.get_bind(), checkfirst=True)
    _TABLE_READY = True


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    s = dt.isoformat()
    # 全项目 utcnow() 实际返回北京时间（UTC+8）naive datetime，序列化时标明 +08:00
    return s if s.endswith("Z") or "+" in s else f"{s}+08:00"


def serialize_item(item: ReviewItem) -> dict:
    return {
        "id": item.id,
        "kind": item.kind,
        "prompt": item.prompt,
        "answer": item.answer,
        "phonetic": item.phonetic or "",
        "note": item.note or "",
        "context_text": item.context_text or "",
        "source_type": item.source_type or "manual",
        "source_session_id": item.source_session_id,
        "scene_id": item.scene_id,
        "scene_name": item.scene_name or "",
        "repetitions": item.repetitions,
        "interval_days": item.interval_days,
        "ease_factor": round(float(item.ease_factor or 2.5), 2),
        "mastery": item.mastery,
        "status": item.status,
        "due_at": _iso(item.due_at),
        "last_reviewed_at": _iso(item.last_reviewed_at),
        "created_at": _iso(item.created_at),
    }


def _compute_streak(items: list[ReviewItem]) -> int:
    dates = {it.last_reviewed_at.date() for it in items if it.last_reviewed_at is not None}
    if not dates:
        return 0
    today = utcnow().date()
    cur = today if today in dates else (today - timedelta(days=1))
    if cur not in dates:
        return 0
    streak = 0
    while cur in dates:
        streak += 1
        cur = cur - timedelta(days=1)
    return streak


def _compute_stats(items: list[ReviewItem]) -> dict:
    now = utcnow()
    active = [it for it in items if it.status != "mastered"]
    due = [it for it in active if it.due_at <= now]
    mastered = [it for it in items if it.status == "mastered"]
    return {
        "total": len(items),
        "active": len(active),
        "due": len(due),
        "mastered": len(mastered),
        "streak_days": _compute_streak(items),
    }


def sync_from_sessions(db: Session, user_id: int) -> int:
    """扫描用户历史练习会话（语法纠错、发音低分词、Agent 标记的 review_tasks），幂等生成复习项。"""
    ensure_review_table(db)
    existing_keys = {
        row[0]
        for row in db.query(ReviewItem.source_key)
        .filter(ReviewItem.user_id == user_id, ReviewItem.source_key.isnot(None))
        .all()
    }

    sessions = (
        db.query(PracticeSession)
        .filter(PracticeSession.user_id == user_id)
        .order_by(PracticeSession.created_at.desc())
        .all()
    )
    if not sessions:
        return 0

    session_ids = [s.id for s in sessions]
    turns = (
        db.query(PracticeTurn)
        .filter(PracticeTurn.session_id.in_(session_ids))
        .order_by(PracticeTurn.session_id, PracticeTurn.number.asc())
        .all()
    )
    turns_by_session: dict[str, list[PracticeTurn]] = {}
    for t in turns:
        turns_by_session.setdefault(t.session_id, []).append(t)

    now = utcnow()
    added = 0

    for sess in sessions:
        snap = sess.scene_snapshot if isinstance(sess.scene_snapshot, dict) else {}
        scene_name = str(snap.get("name") or sess.scene_id or "场景对话")
        sess_turns = turns_by_session.get(sess.id, [])

        prev_ai_text = (sess.greeting or "").strip()
        for t in sess_turns:
            # 1) 语法 / 地道表达纠错
            gc = t.grammar_correction if isinstance(t.grammar_correction, dict) else None
            if gc and gc.get("has_error"):
                source_key = f"corr:{t.id}"
                if source_key not in existing_keys:
                    original = str(gc.get("original") or t.input_text or "").strip()
                    corrected = str(gc.get("corrected") or "").strip()
                    better = [str(x).strip() for x in (gc.get("better_expressions") or []) if str(x).strip()]
                    answer = corrected or (better[0] if better else original)
                    explanation = str(gc.get("explanation") or "").strip()
                    note_parts = [p for p in [explanation, f"地道替换：{' / '.join(better)}" if better else ""] if p]
                    issue_type = str(gc.get("issue_type") or "grammar").lower()
                    kind = "expression" if "expr" in issue_type or "vocab" in issue_type else "grammar"
                    if original and answer:
                        db.add(ReviewItem(
                            user_id=user_id,
                            kind=kind,
                            prompt=f"优化当时表达：{original}",
                            answer=answer,
                            note="\n".join(note_parts),
                            context_text=f"对方说：{prev_ai_text}" if prev_ai_text else "",
                            source_type="correction",
                            source_key=source_key,
                            source_session_id=sess.id,
                            scene_id=sess.scene_id,
                            scene_name=scene_name,
                            due_at=now,
                        ))
                        existing_keys.add(source_key)
                        added += 1

            # 2) 发音评测低分词（每轮取最弱的前 2 个词，避免刷屏）
            ps = t.pronunciation_score if isinstance(t.pronunciation_score, dict) else None
            if ps and isinstance(ps.get("words"), list):
                weak_words = []
                for w in ps["words"]:
                    word_txt = str(w.get("word") or "").strip()
                    raw_score = w.get("score") if w.get("score") is not None else w.get("total_score")
                    if not word_txt or raw_score is None:
                        continue
                    score_val = round(float(raw_score), 1)
                    if score_val < 78:
                        weak_words.append((word_txt, score_val))
                weak_words.sort(key=lambda x: x[1])
                for word_txt, score_val in weak_words[:2]:
                    source_key = f"pron:{t.id}:{word_txt.lower()}"
                    if source_key in existing_keys:
                        continue
                    db.add(ReviewItem(
                        user_id=user_id,
                        kind="pronunciation",
                        prompt=f"发音纠偏：注意单词 \"{word_txt}\"（原评分 {score_val}）",
                        answer=t.input_text or word_txt,
                        phonetic=f"目标词：{word_txt}",
                        note=f"在「{scene_name}」第 {t.number} 轮朗读中该词得分 {score_val}，建议慢速跟读原句巩固。",
                        context_text=f"对方说：{prev_ai_text}" if prev_ai_text else "",
                        source_type="pronunciation",
                        source_key=source_key,
                        source_session_id=sess.id,
                        scene_id=sess.scene_id,
                        scene_name=scene_name,
                        due_at=now,
                    ))
                    existing_keys.add(source_key)
                    added += 1

            resp = t.response_json if isinstance(t.response_json, dict) else {}
            if resp.get("text"):
                prev_ai_text = str(resp["text"]).strip()

        # 3) 对话中 Agent 调用 add_review_task 记入的 review_tasks
        state = sess.state_json if isinstance(sess.state_json, dict) else {}
        sc_state = state.get("scenario_state") if isinstance(state.get("scenario_state"), dict) else {}
        for topic in sc_state.get("review_tasks") or []:
            topic_txt = str(topic or "").strip()
            if not topic_txt:
                continue
            digest = hashlib.sha1(topic_txt.encode("utf-8")).hexdigest()[:12]
            source_key = f"task:{sess.id}:{digest}"
            if source_key in existing_keys:
                continue
            db.add(ReviewItem(
                user_id=user_id,
                kind="expression",
                prompt=f"对话中标记的复习重点：{topic_txt}",
                answer=topic_txt,
                note=f"来自「{scene_name}」练习中 AI 助教为你记录的复习要点。",
                source_type="agent_task",
                source_key=source_key,
                source_session_id=sess.id,
                scene_id=sess.scene_id,
                scene_name=scene_name,
                due_at=now,
            ))
            existing_keys.add(source_key)
            added += 1

    if added:
        db.commit()
    return added


def list_review_payload(db: Session, user_id: int, auto_sync: bool = True) -> dict:
    ensure_review_table(db)
    if auto_sync:
        sync_from_sessions(db, user_id)
    items = (
        db.query(ReviewItem)
        .filter(ReviewItem.user_id == user_id)
        .order_by(ReviewItem.due_at.asc(), ReviewItem.id.desc())
        .all()
    )
    return {
        "items": [serialize_item(it) for it in items],
        "stats": _compute_stats(items),
    }


def create_review_item(db: Session, user_id: int, payload: ReviewItemCreate) -> dict:
    ensure_review_table(db)
    item = ReviewItem(
        user_id=user_id,
        kind=payload.kind,
        prompt=payload.prompt.strip(),
        answer=payload.answer.strip(),
        phonetic=payload.phonetic.strip(),
        note=payload.note.strip(),
        context_text=payload.context_text.strip(),
        source_type="manual",
        scene_name=payload.scene_name.strip() or "手动添加",
        due_at=utcnow(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return serialize_item(item)


def _get_owned_item(db: Session, user_id: int, item_id: int) -> ReviewItem:
    ensure_review_table(db)
    item = db.query(ReviewItem).filter(ReviewItem.id == item_id, ReviewItem.user_id == user_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="复习项不存在")
    return item


def update_review_item(db: Session, user_id: int, item_id: int, payload: ReviewItemUpdate) -> dict:
    item = _get_owned_item(db, user_id, item_id)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if isinstance(v, str):
            v = v.strip()
        setattr(item, k, v)
    if data.get("status") == "active" and item.due_at > utcnow():
        item.due_at = utcnow()
    item.updated_at = utcnow()
    db.commit()
    db.refresh(item)
    return serialize_item(item)


def delete_review_item(db: Session, user_id: int, item_id: int) -> None:
    item = _get_owned_item(db, user_id, item_id)
    db.delete(item)
    db.commit()


def submit_review_result(db: Session, user_id: int, item_id: int, rating: ReviewRating) -> dict:
    item = _get_owned_item(db, user_id, item_id)
    now = utcnow()
    was_due = bool(item.status != "mastered" and (item.due_at is None or item.due_at <= now))
    repetitions = item.repetitions or 0
    interval_days = item.interval_days or 0
    ease_factor = float(item.ease_factor or 2.5)
    mastery = item.mastery or 0
    status = item.status or "active"

    if rating == "again":
        repetitions = 0
        interval_days = 0
        ease_factor = max(1.3, ease_factor - 0.2)
        mastery = max(0, mastery - 1)
        status = "active"
        due_at = now + timedelta(minutes=10)
    elif rating == "hard":
        repetitions = max(1, repetitions)
        interval_days = 1
        ease_factor = max(1.3, ease_factor - 0.1)
        mastery = min(5, max(1, mastery))
        status = "active"
        due_at = now + timedelta(days=1)
    elif rating == "good":
        repetitions += 1
        interval_days = 1 if repetitions <= 1 else (3 if repetitions == 2 else round(interval_days * ease_factor))
        mastery = min(5, mastery + 1)
        status = "mastered" if mastery >= 5 else "active"
        due_at = now + timedelta(days=interval_days)
    else:
        repetitions += 2
        ease_factor = min(3.0, ease_factor + 0.1)
        interval_days = max(7, round((interval_days or 3) * ease_factor))
        mastery = min(5, mastery + 2)
        status = "mastered" if mastery >= 5 else "active"
        due_at = now + timedelta(days=interval_days)

    item.repetitions = repetitions
    item.interval_days = interval_days
    item.ease_factor = round(ease_factor, 2)
    item.mastery = mastery
    item.status = status
    item.due_at = due_at
    item.last_reviewed_at = now
    item.updated_at = now
    db.flush()

    all_items = db.query(ReviewItem).filter(ReviewItem.user_id == user_id).all()
    stats = _compute_stats(all_items)
    xp_gain = 3 + (15 if was_due and stats["due"] == 0 else 0)
    award_xp(db, user_id, xp_gain)
    db.commit()
    db.refresh(item)

    return {
        "item": serialize_item(item),
        "stats": stats,
    }
