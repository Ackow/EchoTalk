"""管理端全业务模块补齐与 SaaS 商业化运营服务层。"""
from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.timeutil import utcnow
from app.models import (
    Chunk,
    DebateSession,
    DebateTopic,
    DebateTurn,
    Document,
    ListeningAttempt,
    PersonalChunk,
    PersonalDocument,
    ReviewItem,
    User,
)
from app.models.saas import (
    CreditLedger,
    CreditTaskDef,
    RedeemCode,
    SaasCampaign,
    SaasPlanConfig,
    SubscriptionOrder,
)
from app.services import saas_service


# ---- 1. 用户会员等级与积分调账 ----
def grant_user_saas(
    db: Session,
    user_id: int,
    *,
    plan_tier: str | None = None,
    plan_days: int | None = None,
    credits_delta: int = 0,
    remark: str = "管理员手动调整",
) -> dict[str, Any]:
    user = db.get(User, user_id)
    if not user:
        raise AppError("用户不存在", code="NOT_FOUND", status_code=404)

    if plan_tier is not None:
        user.plan_tier = plan_tier
        if plan_tier == "free":
            user.plan_expires_at = None
        elif plan_days and plan_days > 0:
            now = utcnow()
            base = user.plan_expires_at if (user.plan_expires_at and user.plan_expires_at > now) else now
            user.plan_expires_at = base + timedelta(days=plan_days)
        elif not user.plan_expires_at:
            user.plan_expires_at = utcnow() + timedelta(days=30)

    if credits_delta != 0:
        saas_service._append_ledger(db, user, credits_delta, "admin_adjust", remark or "管理员调账")

    db.add(user)
    db.commit()
    return {
        "id": user.id,
        "username": user.username,
        "plan_tier": user.plan_tier,
        "plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
        "credits_balance": user.credits_balance,
    }


# ---- 2. 多角色场景（Debate / Panel）管理 ----
def list_admin_debates(
    db: Session,
    *,
    q: str | None = None,
    scene_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    query = db.query(DebateTopic)
    if q and q.strip():
        kw = f"%{q.strip()}%"
        query = query.filter((DebateTopic.title_zh.ilike(kw)) | (DebateTopic.motion_en.ilike(kw)))
    if scene_type:
        query = query.filter(DebateTopic.scene_type == scene_type)
    if status:
        query = query.filter(DebateTopic.status == status)

    total = query.count()
    rows = query.order_by(desc(DebateTopic.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    owner_ids = {r.owner_id for r in rows if r.owner_id}
    owners = {u.id: u.username for u in db.query(User).filter(User.id.in_(owner_ids)).all()} if owner_ids else {}

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": r.id,
                "title_zh": r.title_zh,
                "motion_en": r.motion_en,
                "scene_type": r.scene_type,
                "category_label": r.category_label,
                "difficulty_label": r.difficulty_label,
                "duration": r.duration,
                "status": r.status,
                "required_tier": getattr(r, "required_tier", "free") or "free",
                "is_builtin": bool(r.is_builtin),
                "owner_username": owners.get(r.owner_id, "官方内置" if r.is_builtin else "-"),
                "roles_count": len(r.roles_config or []),
                "roles_config": r.roles_config or [],
                "stages_config": r.stages_config or [],
                "tools_config": r.tools_config or [],
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


def update_admin_debate(db: Session, topic_id: str, data: dict[str, Any]) -> dict[str, Any]:
    topic = db.get(DebateTopic, topic_id)
    if not topic:
        raise AppError("多角色场景不存在", code="NOT_FOUND", status_code=404)
    for k in ("status", "required_tier", "title_zh", "difficulty_label"):
        if k in data and data[k] is not None:
            setattr(topic, k, data[k])
    db.add(topic)
    db.commit()
    return {"id": topic.id, "status": topic.status, "required_tier": topic.required_tier}


def delete_admin_debate(db: Session, topic_id: str) -> None:
    topic = db.get(DebateTopic, topic_id)
    if not topic:
        raise AppError("多角色场景不存在", code="NOT_FOUND", status_code=404)
    if topic.is_builtin:
        raise AppError("官方内置场景不可删除，可设为 private 隐藏", code="FORBIDDEN", status_code=400)
    db.delete(topic)
    db.commit()


# ---- 3. 多角色会话记录管理 ----
def list_admin_debate_sessions(
    db: Session,
    *,
    q: str | None = None,
    scene_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    query = db.query(DebateSession)
    if q and q.strip():
        query = query.filter(DebateSession.topic_title.ilike(f"%{q.strip()}%"))
    if scene_type:
        query = query.filter(DebateSession.scene_type == scene_type)
    if status:
        query = query.filter(DebateSession.status == status)

    total = query.count()
    rows = query.order_by(desc(DebateSession.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    uids = {r.user_id for r in rows}
    users = {u.id: u.username for u in db.query(User).filter(User.id.in_(uids)).all()} if uids else {}

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "username": users.get(r.user_id, f"用户#{r.user_id}"),
                "topic_id": r.topic_id,
                "topic_title": r.topic_title,
                "scene_type": r.scene_type,
                "user_side": r.user_side,
                "turn_count": r.turn_count,
                "win_rate": r.win_rate,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


def get_admin_debate_session_detail(db: Session, session_id: str) -> dict[str, Any]:
    sess = db.get(DebateSession, session_id)
    if not sess:
        raise AppError("多角色会话不存在", code="NOT_FOUND", status_code=404)
    turns = db.query(DebateTurn).filter(DebateTurn.session_id == session_id).order_by(DebateTurn.turn_number.asc(), DebateTurn.id.asc()).all()
    user = db.get(User, sess.user_id)
    return {
        "session": {
            "id": sess.id,
            "username": user.username if user else f"用户#{sess.user_id}",
            "topic_title": sess.topic_title,
            "motion_en": sess.motion_en,
            "scene_type": sess.scene_type,
            "win_rate": sess.win_rate,
            "status": sess.status,
            "scores_json": sess.scores_json,
            "verdict_json": sess.verdict_json,
            "created_at": sess.created_at.isoformat(),
        },
        "turns": [
            {
                "id": t.id,
                "turn_number": t.turn_number,
                "stage_label": t.stage_label,
                "role": t.role,
                "speaker": t.speaker,
                "role_title": t.role_title,
                "en_text": t.en_text,
            }
            for t in turns
        ],
    }


def delete_admin_debate_session(db: Session, session_id: str) -> None:
    sess = db.get(DebateSession, session_id)
    if not sess:
        raise AppError("多角色会话不存在", code="NOT_FOUND", status_code=404)
    db.query(DebateTurn).filter(DebateTurn.session_id == session_id).delete()
    db.delete(sess)
    db.commit()


# ---- 4. 知识库文档管理（场景文档 + 个人知识库） ----
def list_admin_knowledge(
    db: Session,
    *,
    scope: str = "scene",  # scene | personal
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    if scope == "personal":
        query = db.query(PersonalDocument)
        if q and q.strip():
            query = query.filter(PersonalDocument.filename.ilike(f"%{q.strip()}%"))
        total = query.count()
        rows = query.order_by(desc(PersonalDocument.created_at)).offset((page - 1) * page_size).limit(page_size).all()
        uids = {r.owner_id for r in rows}
        users = {u.id: u.username for u in db.query(User).filter(User.id.in_(uids)).all()} if uids else {}
        doc_ids = [r.id for r in rows]
        chunk_counts = dict(db.query(PersonalChunk.document_id, func.count()).filter(PersonalChunk.document_id.in_(doc_ids)).group_by(PersonalChunk.document_id).all()) if doc_ids else {}
        return {
            "total": total,
            "items": [
                {
                    "id": r.id,
                    "scope": "personal",
                    "title": r.filename,
                    "owner": users.get(r.owner_id, f"用户#{r.owner_id}"),
                    "scene_id": "-",
                    "chunk_count": chunk_counts.get(r.id, 0),
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ],
        }

    query = db.query(Document)
    if q and q.strip():
        query = query.filter((Document.filename.ilike(f"%{q.strip()}%")) | (Document.scene_id.ilike(f"%{q.strip()}%")))
    total = query.count()
    rows = query.order_by(desc(Document.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    doc_ids = [r.id for r in rows]
    chunk_counts = dict(db.query(Chunk.document_id, func.count()).filter(Chunk.document_id.in_(doc_ids)).group_by(Chunk.document_id).all()) if doc_ids else {}
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "scope": "scene",
                "title": r.filename,
                "owner": "场景绑定",
                "scene_id": r.scene_id,
                "chunk_count": chunk_counts.get(r.id, 0),
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


def delete_admin_knowledge(db: Session, scope: str, doc_id: int) -> None:
    if scope == "personal":
        doc = db.get(PersonalDocument, doc_id)
        if not doc:
            raise AppError("个人文档不存在", code="NOT_FOUND", status_code=404)
        db.query(PersonalChunk).filter(PersonalChunk.document_id == doc_id).delete()
        db.delete(doc)
        db.commit()
        return
    doc = db.get(Document, doc_id)
    if not doc:
        raise AppError("场景文档不存在", code="NOT_FOUND", status_code=404)
    db.query(Chunk).filter(Chunk.document_id == doc_id).delete()
    db.delete(doc)
    db.commit()


# ---- 5. 复习计划与听力提交记录 ----
def list_admin_reviews(db: Session, page: int = 1, page_size: int = 20, q: str | None = None) -> dict[str, Any]:
    query = db.query(ReviewItem)
    if q and q.strip():
        kw = f"%{q.strip()}%"
        query = query.filter((ReviewItem.prompt.ilike(kw)) | (ReviewItem.answer.ilike(kw)))
    total = query.count()
    rows = query.order_by(desc(ReviewItem.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    uids = {r.user_id for r in rows}
    users = {u.id: u.username for u in db.query(User).filter(User.id.in_(uids)).all()} if uids else {}
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "username": users.get(r.user_id, f"用户#{r.user_id}"),
                "source_type": r.source_type,
                "front_text": r.prompt,
                "back_text": r.answer,
                "repetitions": r.repetitions,
                "interval_days": r.interval_days,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


def delete_admin_review(db: Session, item_id: int) -> None:
    item = db.get(ReviewItem, item_id)
    if not item:
        raise AppError("复习卡片不存在", code="NOT_FOUND", status_code=404)
    db.delete(item)
    db.commit()


def list_admin_listening_attempts(db: Session, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    query = db.query(ListeningAttempt)
    total = query.count()
    rows = query.order_by(desc(ListeningAttempt.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    uids = {r.user_id for r in rows}
    users = {u.id: u.username for u in db.query(User).filter(User.id.in_(uids)).all()} if uids else {}
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "username": users.get(r.user_id, f"用户#{r.user_id}"),
                "unit_id": r.unit_id,
                "exercise_type": r.exercise_type,
                "is_correct": bool(r.is_correct),
                "hints_used": r.hints_used_json or [],
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


# ---- 6. SaaS 套餐、任务、活动、订单与兑换码后台管理 ----
def update_admin_plan(db: Session, tier: str, data: dict[str, Any]) -> dict[str, Any]:
    saas_service.ensure_saas_defaults(db)
    plan = db.get(SaasPlanConfig, tier)
    if not plan:
        raise AppError("套餐不存在", code="NOT_FOUND", status_code=404)
    for k, v in data.items():
        if v is None:
            continue
        if k in ("allow_zip_import", "allow_zip_export"):
            setattr(plan, k, 1 if v else 0)
        else:
            setattr(plan, k, v)
    db.add(plan)
    db.commit()
    return saas_service.list_plans(db)


def list_admin_tasks(db: Session) -> list[dict[str, Any]]:
    saas_service.ensure_saas_defaults(db)
    rows = db.query(CreditTaskDef).order_by(CreditTaskDef.sort_order.asc()).all()
    return [
        {
            "task_code": t.task_code,
            "title": t.title,
            "description": t.description,
            "category": t.category,
            "target_count": t.target_count,
            "reward_credits": t.reward_credits,
            "daily_limit": t.daily_limit,
            "route_path": t.route_path,
            "enabled": bool(t.enabled),
            "sort_order": t.sort_order,
        }
        for t in rows
    ]


def update_admin_task(db: Session, task_code: str, data: dict[str, Any]) -> dict[str, Any]:
    task = db.get(CreditTaskDef, task_code)
    if not task:
        raise AppError("任务不存在", code="NOT_FOUND", status_code=404)
    for k, v in data.items():
        if v is None:
            continue
        setattr(task, k, (1 if v else 0) if k == "enabled" else v)
    db.add(task)
    db.commit()
    return {"task_code": task.task_code, "enabled": bool(task.enabled), "reward_credits": task.reward_credits}


def list_admin_campaigns(db: Session) -> list[dict[str, Any]]:
    rows = db.query(SaasCampaign).order_by(desc(SaasCampaign.id)).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "bonus_multiplier": c.bonus_multiplier,
            "free_actions_json": c.free_actions_json or [],
            "starts_at": c.starts_at.isoformat(),
            "ends_at": c.ends_at.isoformat(),
            "enabled": bool(c.enabled),
        }
        for c in rows
    ]


def create_admin_campaign(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    c = SaasCampaign(
        name=data["name"],
        description=data.get("description", ""),
        bonus_multiplier=data.get("bonus_multiplier", 2.0),
        free_actions_json=data.get("free_actions_json", []),
        starts_at=data["starts_at"],
        ends_at=data["ends_at"],
        enabled=1 if data.get("enabled", True) else 0,
    )
    db.add(c)
    db.commit()
    return {"id": c.id, "name": c.name}


def update_admin_campaign(db: Session, campaign_id: int, data: dict[str, Any]) -> dict[str, Any]:
    c = db.get(SaasCampaign, campaign_id)
    if not c:
        raise AppError("活动不存在", code="NOT_FOUND", status_code=404)
    for k, v in data.items():
        if v is None:
            continue
        setattr(c, k, (1 if v else 0) if k == "enabled" else v)
    db.add(c)
    db.commit()
    return {"id": c.id, "enabled": bool(c.enabled)}


def delete_admin_campaign(db: Session, campaign_id: int) -> None:
    c = db.get(SaasCampaign, campaign_id)
    if not c:
        raise AppError("活动不存在", code="NOT_FOUND", status_code=404)
    db.delete(c)
    db.commit()


def list_admin_orders(db: Session, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    q = db.query(SubscriptionOrder)
    total = q.count()
    rows = q.order_by(desc(SubscriptionOrder.id)).offset((page - 1) * page_size).limit(page_size).all()
    uids = {r.user_id for r in rows}
    users = {u.id: u.username for u in db.query(User).filter(User.id.in_(uids)).all()} if uids else {}
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "order_no": r.order_no,
                "username": users.get(r.user_id, f"用户#{r.user_id}"),
                "order_type": r.order_type,
                "target_tier": r.target_tier,
                "billing_cycle": r.billing_cycle,
                "credits_granted": r.credits_granted,
                "amount_yuan": r.amount_yuan,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


def list_admin_ledger(db: Session, user_id: int | None = None, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    q = db.query(CreditLedger)
    if user_id:
        q = q.filter(CreditLedger.user_id == user_id)
    total = q.count()
    rows = q.order_by(desc(CreditLedger.id)).offset((page - 1) * page_size).limit(page_size).all()
    uids = {r.user_id for r in rows}
    users = {u.id: u.username for u in db.query(User).filter(User.id.in_(uids)).all()} if uids else {}
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "username": users.get(r.user_id, f"用户#{r.user_id}"),
                "delta": r.delta,
                "balance_after": r.balance_after,
                "source_type": r.source_type,
                "action_key": r.action_key,
                "remark": r.remark,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


def list_admin_redeem_codes(db: Session, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    q = db.query(RedeemCode)
    total = q.count()
    rows = q.order_by(desc(RedeemCode.id)).offset((page - 1) * page_size).limit(page_size).all()
    uids = {r.used_by_user_id for r in rows if r.used_by_user_id}
    users = {u.id: u.username for u in db.query(User).filter(User.id.in_(uids)).all()} if uids else {}
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "code": r.code,
                "reward_type": r.reward_type,
                "reward_credits": r.reward_credits,
                "reward_tier": r.reward_tier,
                "reward_days": r.reward_days,
                "is_used": bool(r.is_used),
                "used_by_username": users.get(r.used_by_user_id) if r.used_by_user_id else None,
                "used_at": r.used_at.isoformat() if r.used_at else None,
                "note": r.note,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


def generate_admin_redeem_codes(db: Session, data: dict[str, Any]) -> list[str]:
    prefix = (data.get("prefix") or "ECHO").strip().upper()
    count = int(data.get("count", 5))
    codes = []
    for _ in range(count):
        code = f"{prefix}-{secrets.token_hex(4).upper()}"
        db.add(
            RedeemCode(
                code=code,
                reward_type=data["reward_type"],
                reward_credits=data.get("reward_credits", 0),
                reward_tier=data.get("reward_tier"),
                reward_days=data.get("reward_days", 0),
                note=data.get("note", ""),
            )
        )
        codes.append(code)
    db.commit()
    return codes
