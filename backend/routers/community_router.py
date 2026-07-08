from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db, get_optional_current_user
from models.community import PostFavorite, PostLike
from models.user import User
from schemas.community_schema import CommentCreate, CommentResponse, PostResponse, ReportCreate, TopicResponse
from services.community_service import (
    add_comment, create_post, create_report, delete_comment, delete_post, follow_user,
    get_comments, get_enabled_topics, get_post, get_posts, set_interaction,
)


router = APIRouter(tags=["community"])


@router.get("/posts", response_model=list[PostResponse])
async def list_posts(
    page: int = 1,
    page_size: int = 20,
    topic_id: int | None = None,
    topic_name: str | None = None,
    topic_scope: str | None = None,
    sort: str = "latest",
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_posts(
        db,
        max(page, 1),
        min(max(page_size, 1), 100),
        current_user.id if current_user else None,
        topic_id if topic_id and topic_id > 0 else None,
        topic_name,
        topic_scope,
        sort,
    )


@router.post("/posts", response_model=PostResponse)
async def publish_post(
    content: str | None = Form(default=None),
    topic_ids: str | None = Form(default=None),
    topic_names: str | None = Form(default=None),
    files: list[UploadFile] = File(default=[]),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_post(db, user.id, content, topic_ids, files, topic_names)


@router.get("/posts/{post_id}", response_model=PostResponse)
async def post_detail(
    post_id: int,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_post(db, post_id, current_user.id if current_user else None)


@router.delete("/posts/{post_id}")
async def remove_post(post_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await delete_post(db, user.id, post_id)
    return {"message": "Post deleted"}


@router.post("/posts/{post_id}/likes")
async def like(post_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await set_interaction(db, user.id, post_id, PostLike, True)
    return {"message": "Post liked"}


@router.delete("/posts/{post_id}/likes")
async def unlike(post_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await set_interaction(db, user.id, post_id, PostLike, False)
    return {"message": "Post unliked"}


@router.post("/posts/{post_id}/favorites")
async def favorite(post_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await set_interaction(db, user.id, post_id, PostFavorite, True)
    return {"message": "Post favorited"}


@router.delete("/posts/{post_id}/favorites")
async def unfavorite(post_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await set_interaction(db, user.id, post_id, PostFavorite, False)
    return {"message": "Post unfavorited"}


@router.get("/posts/{post_id}/comments", response_model=list[CommentResponse])
async def comments(post_id: int, db: AsyncSession = Depends(get_db)):
    return await get_comments(db, post_id)


@router.post("/posts/{post_id}/comments", response_model=CommentResponse)
async def comment(post_id: int, payload: CommentCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await add_comment(db, user.id, post_id, payload)


@router.delete("/posts/{post_id}/comments/{comment_id}")
async def remove_comment(post_id: int, comment_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await delete_comment(db, user.id, post_id, comment_id)
    return {"message": "Comment deleted"}


@router.post("/posts/{post_id}/reports")
async def report(post_id: int, payload: ReportCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await create_report(db, user.id, post_id, payload)
    return {"message": "Report submitted"}


@router.get("/topics", response_model=list[TopicResponse])
async def topics(db: AsyncSession = Depends(get_db)):
    return await get_enabled_topics(db)


@router.post("/users/{user_id}/follow")
async def follow(user_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await follow_user(db, user.id, user_id, True)
    return {"message": "User followed"}


@router.delete("/users/{user_id}/follow")
async def unfollow(user_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await follow_user(db, user.id, user_id, False)
    return {"message": "User unfollowed"}
