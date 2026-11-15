"""复习计划 API 路由。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.review import ReviewItemCreate, ReviewItemUpdate, ReviewSubmitIn
from app.services import review_service

router = APIRouter(prefix="/review", tags=["review"])


@router.get("")
def list_review(
    sync: bool = Query(default=True),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return review_service.list_review_payload(db, user.id, auto_sync=sync)


@router.post("/sync")
def sync_review(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    added = review_service.sync_from_sessions(db, user.id)
    payload = review_service.list_review_payload(db, user.id, auto_sync=False)
    return {"added": added, **payload}


@router.post("")
def create_review(payload: ReviewItemCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = review_service.create_review_item(db, user.id, payload)
    return {"item": item}


@router.patch("/{item_id}")
def update_review(
    item_id: int,
    payload: ReviewItemUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = review_service.update_review_item(db, user.id, item_id, payload)
    return {"item": item}


@router.delete("/{item_id}")
def delete_review(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    review_service.delete_review_item(db, user.id, item_id)
    return {"ok": True}


@router.post("/{item_id}/submit")
def submit_review(
    item_id: int,
    payload: ReviewSubmitIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return review_service.submit_review_result(db, user.id, item_id, payload.rating)
