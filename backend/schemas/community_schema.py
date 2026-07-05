from datetime import datetime

from pydantic import BaseModel, Field


class MediaResponse(BaseModel):
    id: int
    media_type: str
    file_url: str
    mime_type: str
    file_size: int
    sort_order: int


class TopicResponse(BaseModel):
    id: int
    name: str


class PostResponse(BaseModel):
    id: int
    user_id: int
    content: str | None
    status: str
    media: list[MediaResponse]
    topics: list[TopicResponse]
    like_count: int
    favorite_count: int
    comment_count: int
    created_at: datetime


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: int | None = Field(default=None, gt=0)


class CommentResponse(BaseModel):
    id: int
    post_id: int
    user_id: int
    parent_id: int | None
    content: str
    created_at: datetime


class ReportCreate(BaseModel):
    target_type: str = Field(default="post", pattern="^(post|comment)$")
    target_id: int | None = Field(default=None, gt=0)
    reason: str = Field(..., min_length=1, max_length=500)


class PageResult(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int
