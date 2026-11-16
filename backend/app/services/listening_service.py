"""听力工作室与全局经验值业务服务。"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from datetime import datetime, timedelta
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.timeutil import utcnow
from app.models.listening import ListeningAttempt, ListeningProgress, ListeningUnit, UserXpState
from app.models.practice import PracticeSession, PracticeTurn
from app.models.review import ReviewItem

DAILY_GOAL_XP = 60

BUILTIN_LISTENING_UNITS: list[dict] = [
    {
        "id": "daily-bank-card",
        "channel": "daily",
        "cet_level": None,
        "cet_section": None,
        "channel_label": "日常精听",
        "level": "B1 · 职场生活",
        "title": "银行柜台：银行卡异常与补办",
        "subtitle": "重点攻克连读（with it / check on）与转折后真实诉求",
        "duration": "4 分钟",
        "xp": 25,
        "accent": "美音 · 1.0× 常速",
        "exercises": [
            {
                "id": "ex-1",
                "type": "word_bank",
                "prompt": "听音频，点击下方单词拼出你听到的句子",
                "audioText": "I would like to check on a problem with my debit card.",
                "zhText": "我想查询一下我的借记卡出了什么问题。",
                "keywords": ["check on", "problem", "debit card"],
                "tokens": ["I", "would", "like", "to", "check", "on", "a", "problem", "with", "my", "debit", "card"],
                "distractors": ["credit", "about", "want"],
                "tip": '注意 "check on a" 连读听起来像 /tʃek ɒn ə/，"debit" 不要和 "credit" 混淆。',
                "errorTag": "连读弱读",
            },
            {
                "id": "ex-2",
                "type": "choice",
                "prompt": "听对话，女士来银行的真正目的是什么？",
                "audioText": "I originally came in to deposit some cash, but the ATM ate my card right before I could finish.",
                "zhText": "我本来是来存现金的，但还没操作完 ATM 机就把我的卡吞了。",
                "keywords": ["originally", "but", "ATM ate my card"],
                "options": [
                    {"key": "A", "text": "To open a brand new savings account."},
                    {"key": "B", "text": "To report that the ATM kept her card."},
                    {"key": "C", "text": "To withdraw cash at the counter."},
                ],
                "answer": "B",
                "tip": '典型转折陷阱："originally ... deposit" 是前情干扰，but 后面的 "ATM ate my card" 才是核心诉求。',
                "errorTag": "转折干扰项",
            },
            {
                "id": "ex-3",
                "type": "cloze",
                "prompt": "听写填空：补全句子中漏掉的连读/数字信息",
                "audioText": "Your replacement card will arrive within five business days.",
                "zhText": "您的新卡将在五个工作日内寄达。",
                "keywords": ["replacement", "five", "business days"],
                "template": "Your ____ card will arrive within ____ business days.",
                "blanks": ["replacement", "five"],
                "tip": '"within five" 中的 /n/ 与 /f/ 衔接较快，数字与单位名词建议一起抓取。',
                "errorTag": "数字时间",
            },
            {
                "id": "ex-4",
                "type": "shadowing",
                "prompt": "Shadowing 跟读：模仿重音与语调节奏",
                "audioText": "Could you please verify your identity with a photo ID?",
                "zhText": "请您出示带照片的身份证件核实身份好吗？",
                "keywords": ["verify", "identity", "photo ID"],
                "chunks": ["Could you please", "verify your identity", "with a photo ID?"],
                "tip": "重音落在 verify（第一音节）和 photo ID 上，句尾疑问句语调轻微上扬。",
                "errorTag": "语音语调",
            },
        ],
    },
    {
        "id": "radio-morning-tech",
        "channel": "radio",
        "cet_level": None,
        "cet_section": None,
        "channel_label": "英语电台 · 晨间简报",
        "level": "B1–B2 · 播客",
        "title": "EchoFM 晨间科技：AI 耳机与实时同传",
        "subtitle": "自然播客语流，适合通勤盲听与语块跟读",
        "duration": "5 分钟",
        "xp": 25,
        "accent": "英音播客 · 清晰",
        "exercises": [
            {
                "id": "rad-1",
                "type": "choice",
                "prompt": "播客主播提到新一代耳机最大的突破是什么？",
                "audioText": "Good morning, listeners. Today we are looking at smart earbuds that translate live conversations with barely a half-second delay.",
                "zhText": "听众朋友们早上好，今天我们来看看几乎只有半秒延迟就能实时翻译对话的智能耳机。",
                "keywords": ["translate live", "half-second delay"],
                "options": [
                    {"key": "A", "text": "Battery life lasting up to seven days."},
                    {"key": "B", "text": "Real-time translation with minimal delay."},
                    {"key": "C", "text": "Automatic noise cancellation in subways."},
                ],
                "answer": "B",
                "tip": '"barely a half-second delay" 意译对应选项中的 "minimal delay"。',
                "errorTag": "同义替换",
            },
            {
                "id": "rad-2",
                "type": "word_bank",
                "prompt": "听电台原声，拼出主播的提醒句",
                "audioText": "However, background noise can still affect accuracy.",
                "zhText": "不过，背景噪音仍然可能影响准确率。",
                "keywords": ["background noise", "affect", "accuracy"],
                "tokens": ["However,", "background", "noise", "can", "still", "affect", "accuracy"],
                "distractors": ["effect", "increase", "always"],
                "tip": "注意区分动词 affect（影响）与名词 effect（效果）。",
                "errorTag": "易混词辨析",
            },
            {
                "id": "rad-3",
                "type": "shadowing",
                "prompt": "电台主播腔调跟读",
                "audioText": "Stay tuned as we test them on a busy street corner.",
                "zhText": "请继续收听，我们将到繁忙的街角实地测试它们。",
                "keywords": ["Stay tuned", "busy street corner"],
                "chunks": ["Stay tuned", "as we test them", "on a busy street corner."],
                "tip": '"Stay tuned" 是英语电台/播客最常用的过渡语，语气轻快连贯。',
                "errorTag": "语音语调",
            },
        ],
    },
    {
        "id": "talks-ted-habit",
        "channel": "talks",
        "cet_level": None,
        "cet_section": None,
        "channel_label": "演讲与访谈",
        "level": "B2 · TED 风格",
        "title": "微习惯的力量：如何坚持每天 5 分钟英语",
        "subtitle": "演讲停顿、排比强调与情感重音训练",
        "duration": "4 分钟",
        "xp": 25,
        "accent": "美音演讲",
        "exercises": [
            {
                "id": "talk-1",
                "type": "word_bank",
                "prompt": "拼出讲者最具感染力的一句话",
                "audioText": "Small steps repeated daily beat massive plans never started.",
                "zhText": "每天重复的小步骤，胜过从未开始的宏大计划。",
                "keywords": ["Small steps", "repeated daily", "beat"],
                "tokens": ["Small", "steps", "repeated", "daily", "beat", "massive", "plans", "never", "started"],
                "distractors": ["often", "better", "always"],
                "tip": "句中 beat 作动词，表示“胜过、打败”。",
                "errorTag": "句法结构",
            },
            {
                "id": "talk-2",
                "type": "shadowing",
                "prompt": "模仿演讲者的停顿与重音",
                "audioText": "Consistency is not about perfection; it is about showing up.",
                "zhText": "坚持不在于完美，而在于每天到场。",
                "keywords": ["Consistency", "perfection", "showing up"],
                "chunks": ["Consistency is not about perfection;", "it is about", "showing up."],
                "tip": '分号处有明显半秒停顿，为后半句 "showing up" 蓄力。',
                "errorTag": "语音语调",
            },
        ],
    },
]


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def sync_builtin_listening(db: Session) -> int:
    """将内置听力单元同步到数据库（幂等），并清理已下线的模拟四六级占位单元。"""
    legacy_ids = (
        "cet4-news-urban",
        "cet4-conv-library",
        "cet4-passage-museum",
        "cet6-conv-internship",
        "cet6-lecture-sleep",
    )
    for lid in legacy_ids:
        legacy = db.get(ListeningUnit, lid)
        if legacy is not None:
            db.delete(legacy)

    count = 0
    bundle_units: list[dict] = []
    bundle_path = Path(__file__).resolve().parents[2] / "data" / "curated_listening_bundle.json"
    if bundle_path.exists():
        try:
            raw = json.loads(bundle_path.read_text(encoding="utf-8"))
            bundle_units = raw.get("units", raw) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
        except Exception:
            bundle_units = []

    seen_ids: set[str] = set()
    for item in [*BUILTIN_LISTENING_UNITS, *bundle_units]:
        unit_id = item.get("id")
        if not unit_id or unit_id in seen_ids:
            continue
        seen_ids.add(unit_id)
        existing = db.get(ListeningUnit, unit_id)
        if existing is None:
            db.add(
                ListeningUnit(
                    id=unit_id,
                    channel=item["channel"],
                    cet_level=item.get("cet_level") if "cet_level" in item else item.get("cetLevel"),
                    cet_section=item.get("cet_section") if "cet_section" in item else item.get("cetSection"),
                    channel_label=item.get("channel_label") or item.get("channelLabel") or "",
                    level=item.get("level") or "",
                    title=item["title"],
                    subtitle=item.get("subtitle") or "",
                    duration=item.get("duration") or "5 分钟",
                    xp=int(item.get("xp") or 25),
                    accent=item.get("accent") or "标准英语",
                    exercises_json=item.get("exercises") or [],
                    is_builtin=True,
                )
            )
            count += 1
    if count:
        db.commit()
    return count


def _get_or_create_xp(db: Session, user_id: int) -> UserXpState:
    state = db.get(UserXpState, user_id)
    today = _today_str()
    if state is None:
        state = UserXpState(
            user_id=user_id,
            total_xp=0,
            today_xp=0,
            today_date=today,
            streak_days=0,
        )
        db.add(state)
        db.flush()
    elif state.today_date != today:
        state.today_xp = 0
        state.today_date = today
    return state


def _award_xp(db: Session, user_id: int, amount: int) -> UserXpState:
    state = _get_or_create_xp(db, user_id)
    if amount > 0:
        if state.today_xp == 0:
            state.streak_days += 1
        state.total_xp += amount
        state.today_xp += amount
    return state


CHECKIN_REWARDS = (5, 8, 10, 12, 15, 18, 25)


def _checkin_reward_for_day(streak_day: int) -> int:
    idx = (max(1, streak_day) - 1) % len(CHECKIN_REWARDS)
    return CHECKIN_REWARDS[idx]


def _apply_auto_checkin(state: UserXpState) -> tuple[bool, int]:
    """若今日尚未签到，则自动完成每日签到并发放阶梯积分。"""
    today = _today_str()
    if (state.last_checkin_date or "") == today:
        return False, 0
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    if state.last_checkin_date == yesterday:
        state.checkin_streak = (state.checkin_streak or 0) + 1
    else:
        state.checkin_streak = 1
    gained_xp = _checkin_reward_for_day(state.checkin_streak)
    if gained_xp > 0:
        if state.today_xp == 0:
            state.streak_days += 1
        state.total_xp += gained_xp
        state.today_xp += gained_xp
    state.last_checkin_date = today
    return True, gained_xp


def daily_checkin(db: Session, user_id: int) -> dict:
    """每日签到领积分（仿 B 站连续签到 7 天循环阶梯奖励，同日重复签到幂等返回）。"""
    UserXpState.__table__.create(bind=db.get_bind(), checkfirst=True)
    state = _get_or_create_xp(db, user_id)
    just_checked_in, gained_xp = _apply_auto_checkin(state)
    if just_checked_in:
        db.commit()
    profile = get_xp_profile(db, user_id)
    return {
        **profile,
        "alreadyCheckedIn": not just_checked_in,
        "gainedXp": gained_xp,
    }


def award_xp(db: Session, user_id: int, amount: int) -> UserXpState | None:
    """供语音对话、复习计划等模块统一发放经验值（不单独提交事务，由调用方统一 commit）。"""
    if amount <= 0:
        return None
    UserXpState.__table__.create(bind=db.get_bind(), checkfirst=True)
    return _award_xp(db, user_id, amount)


def list_units_with_stats(db: Session, user_id: int | None) -> dict:
    """获取听力单元列表及当前用户的真实独立/辅助正确率统计。"""
    public_filter = or_(ListeningUnit.is_builtin.is_(True), ListeningUnit.owner_id.is_(None))
    stmt = select(ListeningUnit).where(
        or_(public_filter, ListeningUnit.owner_id == user_id)
        if user_id is not None
        else public_filter
    ).order_by(ListeningUnit.created_at.asc())
    units = db.scalars(stmt).all()

    progress_map: dict[str, int] = {}
    independent_rate: int | None = None
    assisted_rate: int | None = None
    weak_tags: list[str] = []

    if user_id is not None:
        for p in db.scalars(select(ListeningProgress).where(ListeningProgress.user_id == user_id)).all():
            progress_map[p.unit_id] = p.progress

        attempts = db.scalars(select(ListeningAttempt).where(ListeningAttempt.user_id == user_id)).all()
        ind_attempts = [a for a in attempts if a.is_independent]
        ast_attempts = [a for a in attempts if not a.is_independent]
        if ind_attempts:
            independent_rate = round(sum(1 for a in ind_attempts if a.is_correct) / len(ind_attempts) * 100)
        if ast_attempts:
            assisted_rate = round(sum(1 for a in ast_attempts if a.is_correct) / len(ast_attempts) * 100)

        wrong_tags = Counter(a.error_tag for a in attempts if not a.is_correct and a.error_tag)
        weak_tags = [tag for tag, _ in wrong_tags.most_common(3)]

    return {
        "units": [
            {
                "id": u.id,
                "channel": u.channel,
                "cetLevel": u.cet_level,
                "cetSection": u.cet_section,
                "channelLabel": u.channel_label,
                "level": u.level,
                "title": u.title,
                "subtitle": u.subtitle,
                "duration": u.duration,
                "xp": u.xp,
                "accent": u.accent,
                "progress": progress_map.get(u.id, 0),
                "exercises": u.exercises_json,
            }
            for u in units
        ],
        "stats": {
            "independentRate": independent_rate,
            "assistedRate": assisted_rate,
            "weakTags": weak_tags,
        },
    }


def record_attempt(
    db: Session,
    user_id: int,
    *,
    unit_id: str,
    exercise_id: str,
    exercise_type: str,
    is_correct: bool,
    is_independent: bool,
    hints_used: list[str],
    error_tag: str,
    step_index: int,
    total_steps: int,
) -> dict:
    """记录单题作答并更新单元进度与经验值。"""
    db.add(
        ListeningAttempt(
            user_id=user_id,
            unit_id=unit_id,
            exercise_id=exercise_id,
            exercise_type=exercise_type,
            is_correct=is_correct,
            is_independent=is_independent,
            hints_used_json=hints_used,
            error_tag=error_tag,
        )
    )

    pct = round(((step_index + 1) / max(1, total_steps)) * 100)
    prog = db.scalar(
        select(ListeningProgress).where(
            ListeningProgress.user_id == user_id,
            ListeningProgress.unit_id == unit_id,
        )
    )
    if prog is None:
        prog = ListeningProgress(user_id=user_id, unit_id=unit_id, progress=pct, completed_count=0)
        db.add(prog)
    else:
        prog.progress = max(prog.progress, pct)

    gained_xp = 5 if is_correct else 0
    state = _award_xp(db, user_id, gained_xp)
    db.commit()
    return {"gainedXp": gained_xp, "totalXp": state.total_xp, "todayXp": state.today_xp}


def complete_unit(db: Session, user_id: int, unit_id: str) -> dict:
    """标记单元完成并结算单元 XP。"""
    unit = db.get(ListeningUnit, unit_id)
    xp_reward = unit.xp if unit else 25

    prog = db.scalar(
        select(ListeningProgress).where(
            ListeningProgress.user_id == user_id,
            ListeningProgress.unit_id == unit_id,
        )
    )
    if prog is None:
        prog = ListeningProgress(user_id=user_id, unit_id=unit_id, progress=100, completed_count=1)
        db.add(prog)
    else:
        prog.progress = 100
        prog.completed_count += 1

    state = _award_xp(db, user_id, xp_reward)
    db.commit()
    return {"gainedXp": xp_reward, "totalXp": state.total_xp, "todayXp": state.today_xp}


def import_unit(db: Session, user_id: int | None, payload: dict) -> dict:
    """导入 JSON 听力/真题单元并持久化到数据库（user_id 为 None 时作为全站资源）。"""
    unit_id = str(payload.get("id") or f"custom-{uuid.uuid4().hex[:8]}")
    if db.get(ListeningUnit, unit_id) is not None:
        unit_id = f"{unit_id}-{uuid.uuid4().hex[:4]}"

    unit = ListeningUnit(
        id=unit_id,
        channel=payload.get("channel") or "cet",
        cet_level=payload.get("cetLevel") or "cet4",
        cet_section=payload.get("cetSection") or "news",
        channel_label=payload.get("channelLabel") or "CET · 本地导入",
        level=payload.get("level") or "本地真题",
        title=payload.get("title") or "导入听力单元",
        subtitle=payload.get("subtitle") or "",
        duration=payload.get("duration") or "5 分钟",
        xp=int(payload.get("xp") or 30),
        accent=payload.get("accent") or "自定义",
        exercises_json=payload.get("exercises") or [],
        is_builtin=False,
        owner_id=user_id,
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return {
        "id": unit.id,
        "channel": unit.channel,
        "cetLevel": unit.cet_level,
        "cetSection": unit.cet_section,
        "channelLabel": unit.channel_label,
        "level": unit.level,
        "title": unit.title,
        "subtitle": unit.subtitle,
        "duration": unit.duration,
        "xp": unit.xp,
        "accent": unit.accent,
        "progress": 0,
        "exercises": unit.exercises_json,
    }


def add_listening_review(
    db: Session,
    user_id: int,
    *,
    unit_id: str,
    exercise_id: str,
    prompt: str,
    answer: str,
    note: str,
    context_text: str,
) -> dict:
    """将听力错题写入复习计划（ReviewItem, kind='listening'）。"""
    source_key = f"listening:{unit_id}:{exercise_id}"
    existing = db.scalar(
        select(ReviewItem).where(ReviewItem.user_id == user_id, ReviewItem.source_key == source_key)
    )
    if existing is not None:
        return {"id": existing.id, "created": False}

    item = ReviewItem(
        user_id=user_id,
        kind="listening",
        prompt=prompt,
        answer=answer,
        note=note,
        context_text=context_text,
        source_type="listening",
        source_key=source_key,
        scene_id=unit_id,
        scene_name="听力工作室",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "created": True}


def get_xp_profile(db: Session, user_id: int) -> dict:
    """查询用户真实经验值与基于今日数据库记录计算的每日任务进度（登录/访问时自动完成每日签到）。"""
    state = _get_or_create_xp(db, user_id)
    just_checked_in, gained_checkin_xp = _apply_auto_checkin(state)
    db.commit()

    today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    listen_count = db.scalar(
        select(func.count(ListeningAttempt.id)).where(
            ListeningAttempt.user_id == user_id,
            ListeningAttempt.created_at >= today_start,
        )
    ) or 0
    talk_count = db.scalar(
        select(func.count(PracticeTurn.id))
        .join(PracticeSession, PracticeSession.id == PracticeTurn.session_id)
        .where(PracticeSession.user_id == user_id, PracticeTurn.created_at >= today_start)
    ) or 0
    review_count = db.scalar(
        select(func.count(ReviewItem.id)).where(
            ReviewItem.user_id == user_id,
            ReviewItem.last_reviewed_at >= today_start,
        )
    ) or 0

    checked_in_today = (state.last_checkin_date or "") == _today_str()
    checkin_streak = state.checkin_streak or 0
    today_checkin_xp = _checkin_reward_for_day(checkin_streak or 1)
    next_checkin_xp = _checkin_reward_for_day(checkin_streak if checked_in_today else checkin_streak + 1)

    return {
        "totalXp": state.total_xp,
        "todayXp": state.today_xp,
        "dailyGoalXp": DAILY_GOAL_XP,
        "streakDays": state.streak_days,
        "checkedInToday": checked_in_today,
        "justCheckedIn": just_checked_in,
        "gainedCheckinXp": gained_checkin_xp,
        "todayCheckinXp": today_checkin_xp,
        "checkinStreak": checkin_streak,
        "nextCheckinXp": next_checkin_xp,
        "checkinRewards": list(CHECKIN_REWARDS),
        "dailyQuests": [
            {
                "id": "q-checkin",
                "title": "每日登录自动签到",
                "current": 1 if checked_in_today else 0,
                "target": 1,
                "xp": today_checkin_xp,
                "type": "checkin",
            },
            {"id": "q-listen", "title": "完成 3 道听力微练习", "current": min(3, listen_count), "target": 3, "xp": 25, "route": "listening"},
            {"id": "q-talk", "title": "完成 3 轮语音对话", "current": min(3, talk_count), "target": 3, "xp": 15, "route": "practice"},
            {"id": "q-review", "title": "完成 1 条间隔复习", "current": min(1, review_count), "target": 1, "xp": 15, "route": "review"},
        ],
    }


def admin_list_units(db: Session) -> list[dict]:
    """管理端：列出所有听力单元（含内置与导入）。"""
    units = db.scalars(select(ListeningUnit).order_by(ListeningUnit.created_at.desc())).all()
    return [
        {
            "id": u.id,
            "channel": u.channel,
            "cetLevel": u.cet_level,
            "cetSection": u.cet_section,
            "channelLabel": u.channel_label,
            "level": u.level,
            "title": u.title,
            "subtitle": u.subtitle,
            "duration": u.duration,
            "xp": u.xp,
            "accent": u.accent,
            "isBuiltin": u.is_builtin,
            "exerciseCount": len(u.exercises_json or []),
            "exercises": u.exercises_json or [],
            "createdAt": u.created_at.isoformat() if u.created_at else None,
        }
        for u in units
    ]


def admin_delete_unit(db: Session, unit_id: str) -> bool:
    """管理端：删除指定听力单元及关联进度/记录。"""
    unit = db.get(ListeningUnit, unit_id)
    if unit is None:
        return False
    for row in db.scalars(select(ListeningProgress).where(ListeningProgress.unit_id == unit_id)).all():
        db.delete(row)
    for row in db.scalars(select(ListeningAttempt).where(ListeningAttempt.unit_id == unit_id)).all():
        db.delete(row)
    db.delete(unit)
    db.commit()
    return True
