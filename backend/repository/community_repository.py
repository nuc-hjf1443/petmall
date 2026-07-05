from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.community import (
    Follow,
    Post,
    PostComment,
    PostFavorite,
    PostLike,
    PostStatus,
    Report,
    Topic,
)


async def get_visible_post(db: AsyncSession, post_id: int) -> Post | None:
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.media), selectinload(Post.topics))
        .where(Post.id == post_id, Post.status == PostStatus.VISIBLE.value)
    )
    return result.scalar_one_or_none()


async def list_visible_posts(db: AsyncSession, page: int, page_size: int) -> list[Post]:
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.media), selectinload(Post.topics))
        .where(Post.status == PostStatus.VISIBLE.value)
        .order_by(Post.created_at.desc(), Post.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().unique().all())


async def interaction_counts(db: AsyncSession, post_id: int) -> tuple[int, int, int]:
    values = []
    for model in (PostLike, PostFavorite, PostComment):
        filters = [model.post_id == post_id]
        if model is PostComment:
            filters.append(model.is_deleted.is_(False))
        values.append(int((await db.scalar(select(func.count(model.id)).where(*filters))) or 0))
    return values[0], values[1], values[2]


async def list_enabled_topics(db: AsyncSession) -> list[Topic]:
    return list((await db.execute(select(Topic).where(Topic.is_enabled.is_(True)).order_by(Topic.name))).scalars())


async def get_topics(db: AsyncSession, ids: list[int]) -> list[Topic]:
    return list((await db.execute(select(Topic).where(Topic.id.in_(ids), Topic.is_enabled.is_(True)))).scalars())


async def get_comment(db: AsyncSession, comment_id: int) -> PostComment | None:
    return (await db.execute(select(PostComment).where(PostComment.id == comment_id))).scalar_one_or_none()


async def get_interaction(db: AsyncSession, model, user_id: int, post_id: int):
    return (
        await db.execute(select(model).where(model.user_id == user_id, model.post_id == post_id))
    ).scalar_one_or_none()


async def get_follow(db: AsyncSession, follower_id: int, followed_id: int) -> Follow | None:
    return (
        await db.execute(
            select(Follow).where(Follow.follower_id == follower_id, Follow.followed_id == followed_id)
        )
    ).scalar_one_or_none()


async def get_report(db: AsyncSession, report_id: int, lock: bool = False) -> Report | None:
    statement = select(Report).where(Report.id == report_id)
    if lock:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one_or_none()
