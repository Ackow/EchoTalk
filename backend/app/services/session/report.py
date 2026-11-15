"""练习会话多维评分报告生成。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PracticeTurn
from app.services.session.crud import owned_session


def get_session_report(db: Session, user_id: int, session_id: str) -> dict:
    """汇总本场练习的多维评分报告（充分利用讯飞 ISE 发音/语调/连读/流利度/逐词分 + 语法纠错 + 目标完成度）。"""
    row = owned_session(db, session_id, user_id)
    turns = db.scalars(select(PracticeTurn).where(PracticeTurn.session_id == session_id).order_by(PracticeTurn.number)).all()
    state = row.state_json or {}
    snapshot = row.scene_snapshot or {}
    meta = snapshot.get("meta") or {}
    goals = state.get("goals") or []
    goals_done = sum(1 for g in goals if g.get("done"))
    goals_total = len(goals)
    task_score = round(goals_done / goals_total * 100) if goals_total else 100

    voice_scores = [t.pronunciation_score for t in turns if isinstance(t.pronunciation_score, dict)]
    grammar_items = [t for t in turns if isinstance(t.grammar_correction, dict)]

    def _avg(key: str) -> float | None:
        vals = [float(s[key]) for s in voice_scores if s.get(key) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    pronunciation_dims = None
    weak_words: list[dict] = []
    strong_words: list[dict] = []
    turn_scores: list[dict] = []
    if voice_scores:
        for t in turns:
            ps = t.pronunciation_score
            if not isinstance(ps, dict):
                continue
            turn_scores.append({
                "turn": t.number,
                "total": round(float(ps.get("total_score") or 0), 1),
                "accuracy": round(float(ps.get("accuracy_score") or 0), 1),
                "fluency": round(float(ps.get("fluency_score") or 0), 1),
                "wpm": round(float(ps.get("speech_rate_wpm") or 0)),
            })
        avg_wpm = _avg("speech_rate_wpm")
        rate_level = "unknown"
        if avg_wpm is not None:
            rate_level = "slow" if avg_wpm < 100 else ("natural" if avg_wpm <= 150 else "fast")
        pronunciation_dims = {
            "voice_turn_count": len(voice_scores),
            "total_score": _avg("total_score"),
            "accuracy_score": _avg("accuracy_score"),
            "fluency_score": _avg("fluency_score"),
            "integrity_score": _avg("integrity_score"),
            "intonation_score": _avg("intonation_score"),
            "liaison_score": _avg("liaison_score"),
            "avg_wpm": round(avg_wpm) if avg_wpm is not None else 0,
            "rate_level": rate_level,
            "has_mock": any(bool(s.get("is_mock")) for s in voice_scores),
        }
        word_best: dict[str, float] = {}
        word_worst: dict[str, float] = {}
        for s in voice_scores:
            for w in s.get("words") or []:
                word_txt = str(w.get("word") or "").strip()
                raw_score = w.get("score") if w.get("score") is not None else w.get("total_score")
                if not word_txt or raw_score is None:
                    continue
                val = round(float(raw_score), 1)
                key = word_txt.lower()
                if key not in word_worst or val < word_worst[key][1]:
                    word_worst[key] = (word_txt, val)
                if key not in word_best or val > word_best[key][1]:
                    word_best[key] = (word_txt, val)
        weak_words = [{"word": txt, "score": sc} for txt, sc in sorted(word_worst.values(), key=lambda x: x[1]) if sc < 78][:8]
        strong_words = [{"word": txt, "score": sc} for txt, sc in sorted(word_best.values(), key=lambda x: -x[1]) if sc >= 88][:6]

    corrections: list[dict] = []
    natural_count = 0
    for t in grammar_items:
        gc = t.grammar_correction
        if gc.get("has_error"):
            corrections.append({
                "turn_number": t.number,
                "original": gc.get("original") or t.input_text,
                "corrected": gc.get("corrected") or "",
                "issue_type": gc.get("issue_type") or "grammar",
                "explanation": gc.get("explanation") or "",
                "better_expressions": gc.get("better_expressions") or [],
            })
        else:
            natural_count += 1

    grammar_score = round((natural_count + len(corrections) * 0.55) / len(grammar_items) * 100) if grammar_items else (85 if turns else 0)

    if pronunciation_dims and pronunciation_dims["total_score"] is not None:
        overall_score = round(
            pronunciation_dims["total_score"] * 0.5
            + grammar_score * 0.3
            + task_score * 0.2
        )
    elif turns:
        overall_score = min(85, round(grammar_score * 0.55 + task_score * 0.30))
    else:
        overall_score = 0

    tips: list[str] = []
    if pronunciation_dims:
        dim_map = [
            ("accuracy_score", "发音准确度"),
            ("fluency_score", "口语流利度"),
            ("intonation_score", "语调韵律"),
            ("liaison_score", "连读自然度"),
        ]
        valid_dims = [(label, pronunciation_dims[k]) for k, label in dim_map if pronunciation_dims.get(k) is not None]
        if valid_dims:
            lowest_label, lowest_val = min(valid_dims, key=lambda x: x[1])
            if lowest_val < 85:
                tips.append(f"本次语音评测中「{lowest_label}」（{lowest_val} 分）相对有提升空间，可针对性跟读回放。")
        if pronunciation_dims["rate_level"] == "slow":
            tips.append(f"平均语速为 {pronunciation_dims['avg_wpm']} WPM（偏慢），建议成组连贯说出意群，减少词间停顿。")
        elif pronunciation_dims["rate_level"] == "fast":
            tips.append(f"平均语速为 {pronunciation_dims['avg_wpm']} WPM（偏快），注意句尾重读与元音饱满度。")
    elif turns:
        tips.append("本次练习未检测到语音录音，缺少发音评测维度（总分已按纯文字作答折算），建议下次点击麦克风开口练习。")
    if weak_words:
        tips.append("重点巩固低分词汇：" + "、".join(w["word"] for w in weak_words[:4]) + "。")
    if corrections:
        tips.append(f"共发现 {len(corrections)} 处可优化表达，建议结合推荐句型再朗读一遍。")
    if not tips and turns and pronunciation_dims:
        tips.append("整体发音清晰自然，表达贴合场景，继续保持当前节奏！")

    return {
        "session_id": row.id,
        "scene_name": meta.get("name") or row.scene_id,
        "status": state.get("status") or "active",
        "turn_count": len(turns),
        "overall_score": overall_score,
        "task_score": task_score,
        "goals_done": goals_done,
        "goals_total": goals_total,
        "grammar_score": grammar_score,
        "pronunciation": pronunciation_dims,
        "turn_scores": turn_scores,
        "weak_words": weak_words,
        "strong_words": strong_words,
        "corrections": corrections,
        "tips": tips,
    }
