"""成长分析聚合服务：基于用户历史会话与轮次数据生成多维能力与趋势分析。"""
from collections import defaultdict
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timeutil import utcnow
from app.models import PracticeSession, PracticeTurn

_CATEGORY_LABELS = {
    "daily": "日常对话",
    "travel": "旅行出行",
    "business": "商务沟通",
    "career": "职场面试",
    "interview": "模拟面试",
    "academic": "学术交流",
    "debate": "多角色辩论",
    "custom": "自定义场景",
}

_ISSUE_LABELS = {
    "grammar": "语法结构",
    "tense": "时态一致",
    "vocabulary": "词汇搭配",
    "expression": "地道表达",
    "preposition": "介词冠词",
    "plural": "单复数",
    "word_order": "语序问题",
    "spelling": "拼写/用词",
    "collocation": "固定搭配",
}


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def _grammar_score(natural_count: int, error_count: int) -> int | None:
    total = natural_count + error_count
    if total == 0:
        return None
    return round((natural_count + error_count * 0.55) / total * 100)


def get_growth_analytics(db: Session, user_id: int, days: int = 30) -> dict:
    """按时间范围聚合用户的练习会话、发音维度、语法错因、场景分布与薄弱词。"""
    cutoff = utcnow() - timedelta(days=days) if days > 0 else None

    session_stmt = (
        select(PracticeSession)
        .where(PracticeSession.user_id == user_id)
        .order_by(PracticeSession.created_at.asc())
    )
    if cutoff is not None:
        session_stmt = session_stmt.where(PracticeSession.created_at >= cutoff)
    sessions = db.scalars(session_stmt).all()

    if not sessions:
        return _empty_analytics(days)

    session_ids = [s.id for s in sessions]
    turns = db.scalars(
        select(PracticeTurn)
        .where(PracticeTurn.session_id.in_(session_ids))
        .order_by(PracticeTurn.created_at.asc())
    ).all()

    turns_by_session: dict[str, list[PracticeTurn]] = defaultdict(list)
    for t in turns:
        turns_by_session[t.session_id].append(t)

    # 仅统计有实际对话轮次的会话，避免空开场会话拉低指标
    active_sessions = [s for s in sessions if turns_by_session.get(s.id)]
    if not active_sessions:
        return _empty_analytics(days)

    finished_count = 0
    goals_done = 0
    goals_total = 0
    category_buckets: dict[str, dict] = defaultdict(lambda: {"sessions": 0, "turns": 0})

    for s in active_sessions:
        state = s.state_json or {}
        if state.get("status") == "finished":
            finished_count += 1
        for g in state.get("goals") or []:
            goals_total += 1
            if g.get("done"):
                goals_done += 1
        meta = (s.scene_snapshot or {}).get("meta") or {}
        cat = str(meta.get("category") or "custom").strip().lower()
        category_buckets[cat]["sessions"] += 1
        category_buckets[cat]["turns"] += len(turns_by_session[s.id])

    dim_keys = ("total_score", "accuracy_score", "fluency_score", "integrity_score", "intonation_score", "liaison_score")
    dim_values: dict[str, list[float]] = {k: [] for k in dim_keys}
    wpm_values: list[float] = []
    word_scores: dict[str, list[float]] = defaultdict(list)

    natural_total = 0
    error_total = 0
    issue_counts: dict[str, int] = defaultdict(int)

    daily_buckets: dict[str, dict] = defaultdict(
        lambda: {
            "sessions": set(),
            "turns": 0,
            "pron_scores": [],
            "natural": 0,
            "errors": 0,
        }
    )

    active_turns = [t for s in active_sessions for t in turns_by_session[s.id]]
    for t in active_turns:
        day_key = t.created_at.strftime("%Y-%m-%d")
        bucket = daily_buckets[day_key]
        bucket["sessions"].add(t.session_id)
        bucket["turns"] += 1

        ps = t.pronunciation_score
        if isinstance(ps, dict):
            for k in dim_keys:
                if ps.get(k) is not None:
                    val = float(ps[k])
                    dim_values[k].append(val)
                    if k == "total_score":
                        bucket["pron_scores"].append(val)
            if ps.get("speech_rate_wpm") is not None:
                wpm_values.append(float(ps["speech_rate_wpm"]))
            for w in ps.get("words") or []:
                word_txt = str(w.get("word") or "").strip().lower()
                if word_txt and w.get("score") is not None:
                    word_scores[word_txt].append(float(w["score"]))

        gc = t.grammar_correction
        if isinstance(gc, dict):
            if gc.get("has_error"):
                error_total += 1
                bucket["errors"] += 1
                issue_type = str(gc.get("issue_type") or "grammar").strip().lower()
                issue_counts[issue_type] += 1
            else:
                natural_total += 1
                bucket["natural"] += 1

    avg_grammar = _grammar_score(natural_total, error_total)
    avg_pronunciation = _avg(dim_values["total_score"])
    avg_wpm = round(sum(wpm_values) / len(wpm_values)) if wpm_values else None
    task_rate = round(goals_done / goals_total * 100) if goals_total else None

    radar = {
        "has_pronunciation": bool(dim_values["total_score"]),
        "accuracy": _avg(dim_values["accuracy_score"]),
        "fluency": _avg(dim_values["fluency_score"]),
        "intonation": _avg(dim_values["intonation_score"]),
        "liaison": _avg(dim_values["liaison_score"]),
        "integrity": _avg(dim_values["integrity_score"]),
        "grammar": avg_grammar,
    }

    trend = []
    for day_key in sorted(daily_buckets.keys()):
        b = daily_buckets[day_key]
        trend.append({
            "date": day_key[5:],  # MM-DD
            "full_date": day_key,
            "sessions": len(b["sessions"]),
            "turns": b["turns"],
            "pronunciation": _avg(b["pron_scores"]),
            "grammar": _grammar_score(b["natural"], b["errors"]),
        })

    error_distribution = [
        {
            "type": k,
            "label": _ISSUE_LABELS.get(k, k),
            "count": count,
        }
        for k, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
    ][:8]

    category_distribution = [
        {
            "category": cat,
            "label": _CATEGORY_LABELS.get(cat, cat),
            "sessions": info["sessions"],
            "turns": info["turns"],
        }
        for cat, info in sorted(category_buckets.items(), key=lambda x: x[1]["turns"], reverse=True)
    ]

    weak_words = [
        {
            "word": word,
            "avg_score": round(sum(scores) / len(scores), 1),
            "count": len(scores),
        }
        for word, scores in word_scores.items()
    ]
    weak_words = sorted(
        [w for w in weak_words if w["avg_score"] < 85],
        key=lambda x: (x["avg_score"], -x["count"]),
    )[:10]

    recommendations = _build_recommendations(
        radar=radar,
        error_distribution=error_distribution,
        weak_words=weak_words,
        avg_wpm=avg_wpm,
        task_rate=task_rate,
    )

    return {
        "range_days": days,
        "summary": {
            "session_count": len(active_sessions),
            "finished_count": finished_count,
            "turn_count": len(active_turns),
            "voice_turn_count": len(dim_values["total_score"]),
            "avg_pronunciation": avg_pronunciation,
            "avg_grammar": avg_grammar,
            "avg_wpm": avg_wpm,
            "task_completion_rate": task_rate,
            "goals_done": goals_done,
            "goals_total": goals_total,
        },
        "radar": radar,
        "trend": trend,
        "error_distribution": error_distribution,
        "category_distribution": category_distribution,
        "weak_words": weak_words,
        "recommendations": recommendations,
    }


def _empty_analytics(days: int) -> dict:
    return {
        "range_days": days,
        "summary": {
            "session_count": 0,
            "finished_count": 0,
            "turn_count": 0,
            "voice_turn_count": 0,
            "avg_pronunciation": None,
            "avg_grammar": None,
            "avg_wpm": None,
            "task_completion_rate": None,
            "goals_done": 0,
            "goals_total": 0,
        },
        "radar": {
            "has_pronunciation": False,
            "accuracy": None,
            "fluency": None,
            "intonation": None,
            "liaison": None,
            "integrity": None,
            "grammar": None,
        },
        "trend": [],
        "error_distribution": [],
        "category_distribution": [],
        "weak_words": [],
        "recommendations": [],
    }


def _build_recommendations(
    radar: dict,
    error_distribution: list[dict],
    weak_words: list[dict],
    avg_wpm: int | None,
    task_rate: int | None,
) -> list[dict]:
    recs: list[dict] = []

    pron_dims = [
        ("accuracy", "发音准确度", "多做慢速跟读与音素对比，重点巩固高频低分单词。"),
        ("fluency", "口语流利度", "尝试用完整短语而非逐词输出，减少句中停顿。"),
        ("intonation", "语调韵律", "留意疑问句升调与陈述句降调的自然起伏。"),
        ("liaison", "连读自然度", "注意辅音+元音连读与常见弱读词（to / of / and）。"),
    ]
    available_dims = [(label, radar[k], desc) for k, label, desc in pron_dims if radar.get(k) is not None]
    if available_dims:
        weakest_label, weakest_val, weakest_desc = min(available_dims, key=lambda x: x[1])
        if weakest_val < 85:
            recs.append({
                "title": f"发音重点 · {weakest_label}（{weakest_val} 分）",
                "detail": weakest_desc,
                "action_label": "去语音练习",
                "route_name": "practice",
            })

    if error_distribution:
        top_err = error_distribution[0]
        recs.append({
            "title": f"高频表达问题 · {top_err['label']}（{top_err['count']} 次）",
            "detail": "可在历史记录中打开对应场次的练习报告，复盘每轮纠错对比。",
            "action_label": "查看历史记录",
            "route_name": "history",
        })

    if weak_words:
        sample = " / ".join(w["word"] for w in weak_words[:3])
        recs.append({
            "title": f"重点巩固词汇 · {sample}",
            "detail": "这些词在近期语音评测中得分偏低，建议在场景对话中刻意复用。",
            "action_label": "探索新场景",
            "route_name": "scenes",
        })
    elif avg_wpm is not None and avg_wpm < 100:
        recs.append({
            "title": f"语速提升空间 · 当前 {avg_wpm} WPM",
            "detail": "当前语速偏慢，熟悉常用表达后可尝试加快到 110–140 WPM 的自然节奏。",
            "action_label": "开始对话练习",
            "route_name": "practice",
        })
    elif task_rate is not None and task_rate < 80:
        recs.append({
            "title": f"场景目标完成率 {task_rate}%",
            "detail": "练习时可留意右侧目标清单，尽量在对话中主动推进并完成所有任务。",
            "action_label": "继续练习",
            "route_name": "practice",
        })

    if not recs:
        recs.append({
            "title": "保持当前训练节奏",
            "detail": "近期各项指标表现稳定，可以尝试更高难度或不同领域的对话场景。",
            "action_label": "探索场景",
            "route_name": "scenes",
        })

    return recs[:3]
