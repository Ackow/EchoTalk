from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user, get_current_user, get_db, get_optional_user
from app.models.user import User
from app.services import saas_service
from app.services.listening_service import (
    add_listening_review,
    admin_delete_unit,
    admin_list_units,
    complete_unit,
    daily_checkin,
    get_xp_profile,
    import_unit,
    list_units_with_stats,
    record_attempt,
)
from app.services.tts_service import TEXT_MAX, normalize_style, synthesize

router = APIRouter(tags=["listening"])

_AUDIO_CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "listening_audio_cache"


class AttemptCreateRequest(BaseModel):
    unitId: str
    exerciseId: str
    exerciseType: str
    isCorrect: bool
    isIndependent: bool
    hintsUsed: list[str] = Field(default_factory=list)
    errorTag: str = ""
    stepIndex: int = 0
    totalSteps: int = 1


class ReviewAddRequest(BaseModel):
    unitId: str
    exerciseId: str
    prompt: str
    answer: str
    note: str = ""
    contextText: str = ""


class AdminImportPayload(BaseModel):
    id: str | None = None
    channel: str = "cet"
    cetLevel: str | None = "cet4"
    cetSection: str | None = "news"
    channelLabel: str = "CET · 真题导入"
    level: str = "四级真题风"
    title: str
    subtitle: str = ""
    duration: str = "5 分钟"
    xp: int = 30
    accent: str = "标准美音"
    exercises: list[dict[str, Any]] = Field(default_factory=list)


@router.get("/listening/units")
def get_listening_units(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    return list_units_with_stats(db, current_user.id if current_user else None)


@router.post("/listening/attempts")
def create_listening_attempt(
    payload: AttemptCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    res = record_attempt(
        db,
        current_user.id,
        unit_id=payload.unitId,
        exercise_id=payload.exerciseId,
        exercise_type=payload.exerciseType,
        is_correct=payload.isCorrect,
        is_independent=payload.isIndependent,
        hints_used=payload.hintsUsed,
        error_tag=payload.errorTag,
        step_index=payload.stepIndex,
        total_steps=payload.totalSteps,
    )
    saas_service.record_task_progress(db, current_user.id, "daily_listening_1")
    return res


@router.post("/listening/units/{unit_id}/complete")
def finish_listening_unit(
    unit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    res = complete_unit(db, current_user.id, unit_id)
    saas_service.record_task_progress(db, current_user.id, "daily_listening_1")
    return res


@router.post("/listening/review-add")
def add_to_listening_review(
    payload: ReviewAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return add_listening_review(
        db,
        current_user.id,
        unit_id=payload.unitId,
        exercise_id=payload.exerciseId,
        prompt=payload.prompt,
        answer=payload.answer,
        note=payload.note,
        context_text=payload.contextText,
    )


@router.get("/listening/profile")
def get_listening_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return get_xp_profile(db, current_user.id)


@router.post("/listening/checkin")
def post_daily_checkin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return daily_checkin(db, current_user.id)


def _split_tts_chunks(text: str, limit: int = TEXT_MAX) -> list[str]:
    """按句末标点将长文本拆分为不超过 limit 的片段，避免超出单次 TTS 长度限制。"""
    if len(text) <= limit:
        return [text]
    import re
    sentences = [s.strip() for s in re.split(r"(?<=[。！？.!?])\s+", text) if s.strip()]
    chunks: list[str] = []
    current = ""
    for sent in sentences:
        if len(sent) > limit:
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(sent), limit):
                chunks.append(sent[i : i + limit])
            continue
        candidate = f"{current} {sent}".strip() if current else sent
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = sent
    if current:
        chunks.append(current)
    return chunks or [text[:limit]]


@router.get("/listening/audio")
async def stream_listening_audio(
    text: str = Query(..., min_length=1, max_length=2000),
    rate: float = Query(1.0, ge=0.5, le=1.5),
    style: str = Query("emma", max_length=40),
) -> Response:
    clean_text = text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="text 不能为空")

    resolved_style = normalize_style(style) or "emma"
    cache_key = hashlib.sha256(f"{resolved_style}|{rate:.2f}|{clean_text}".encode("utf-8")).hexdigest()
    _AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _AUDIO_CACHE_DIR / f"{cache_key}.mp3"

    if cache_file.exists():
        audio_bytes = cache_file.read_bytes()
    else:
        try:
            parts = []
            for part in _split_tts_chunks(clean_text, TEXT_MAX):
                parts.append(await synthesize(text=part, style=resolved_style, speech_rate=rate))
            audio_bytes = b"".join(parts)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"音频合成失败：{exc}") from exc
        if audio_bytes:
            cache_file.write_bytes(audio_bytes)

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/admin/listening/units")
def list_admin_listening_units(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> dict:
    return {"items": admin_list_units(db)}


@router.post("/admin/listening/import")
def import_admin_listening_units(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> dict:
    raw_units = payload.get("units") if isinstance(payload.get("units"), list) else [payload]
    imported = []
    for raw in raw_units:
        parsed = AdminImportPayload.model_validate(raw)
        if not parsed.exercises:
            raise HTTPException(status_code=400, detail=f"单元「{parsed.title}」缺少 exercises 题目列表")
        imported.append(import_unit(db, None, parsed.model_dump()))
    return {"imported": len(imported), "items": imported}


@router.delete("/admin/listening/units/{unit_id}")
def delete_admin_listening_unit(
    unit_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> dict:
    deleted = admin_delete_unit(db, unit_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="未找到对应听力单元")
    return {"deleted": True, "id": unit_id}
