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
    PostTopic,
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


async def list_visible_posts(
    db: AsyncSession,
    page: int,
    page_size: int,
    topic_id: int | None = None,
    *,
    exclude_topic_names: list[str] | None = None,
    sort: str = "latest",
) -> list[Post]:
    statement = (
        select(Post)
        .options(selectinload(Post.media), selectinload(Post.topics))
        .where(Post.status == PostStatus.VISIBLE.value)
    )
    if topic_id is not None:
        statement = statement.join(PostTopic, PostTopic.post_id == Post.id).where(PostTopic.topic_id == topic_id)
    if exclude_topic_names:
        excluded_topic_ids = select(Topic.id).where(
            Topic.name.in_(exclude_topic_names),
            Topic.is_enabled.is_(True),
        )
        posts_with_excluded_topics = select(PostTopic.post_id).where(PostTopic.topic_id.in_(excluded_topic_ids))
        statement = statement.where(Post.id.not_in(posts_with_excluded_topics))
    if sort == "recommend":
        like_count = (
            select(func.count(PostLike.id))
            .where(PostLike.post_id == Post.id)
            .correlate(Post)
            .scalar_subquery()
        )
        favorite_count = (
            select(func.count(PostFavorite.id))
            .where(PostFavorite.post_id == Post.id)
            .correlate(Post)
            .scalar_subquery()
        )
        comment_count = (
            select(func.count(PostComment.id))
            .where(PostComment.post_id == Post.id, PostComment.is_deleted.is_(False))
            .correlate(Post)
            .scalar_subquery()
        )
        statement = statement.order_by(
            (like_count + favorite_count + comment_count).desc(),
            Post.created_at.desc(),
            Post.id.desc(),
        )
    else:
        statement = statement.order_by(Post.created_at.desc(), Post.id.desc())
    result = await db.execute(
        statement
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


async def ensure_topics(db: AsyncSession, names: list[str]) -> list[Topic]:
    existing = {
        topic.name: topic
        for topic in (await db.execute(select(Topic).where(Topic.name.in_(names)))).scalars()
    }
    missing = [Topic(name=name, is_enabled=True) for name in names if name not in existing]
    if missing:
        db.add_all(missing)
        await db.commit()
    return await list_enabled_topics(db)


async def get_topics(db: AsyncSession, ids: list[int]) -> list[Topic]:
    return list((await db.execute(select(Topic).where(Topic.id.in_(ids), Topic.is_enabled.is_(True)))).scalars())


async def get_topic_by_name(db: AsyncSession, name: str) -> Topic | None:
    return (
        await db.execute(select(Topic).where(Topic.name == name, Topic.is_enabled.is_(True)))
    ).scalar_one_or_none()


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
