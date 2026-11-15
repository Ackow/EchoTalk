"""复习计划请求与响应模型。"""
from typing import Literal

from pydantic import BaseModel, Field

ReviewKind = Literal["expression", "pronunciation", "grammar", "listening"]
ReviewStatus = Literal["active", "mastered"]
ReviewRating = Literal["again", "hard", "good", "easy"]


class ReviewItemCreate(BaseModel):
    kind: ReviewKind = "expression"
    prompt: str = Field(min_length=1, max_length=1000)
    answer: str = Field(min_length=1, max_length=1000)
    phonetic: str = Field(default="", max_length=255)
    note: str = Field(default="", max_length=2000)
    context_text: str = Field(default="", max_length=2000)
    scene_name: str = Field(default="", max_length=120)


class ReviewItemUpdate(BaseModel):
    kind: ReviewKind | None = None
    prompt: str | None = Field(default=None, min_length=1, max_length=1000)
    answer: str | None = Field(default=None, min_length=1, max_length=1000)
    phonetic: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=2000)
    context_text: str | None = Field(default=None, max_length=2000)
    scene_name: str | None = Field(default=None, max_length=120)
    status: ReviewStatus | None = None
    mastery: int | None = Field(default=None, ge=0, le=5)


class ReviewSubmitIn(BaseModel):
    rating: ReviewRating
