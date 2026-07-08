import json
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import bad_request, conflict, forbidden, not_found
from models.community import Follow, Post, PostComment, PostFavorite, PostLike, PostMedia, PostStatus, Report
from models.user import User
from repository.community_repository import (
    ensure_topics,
    get_comment,
    get_follow,
    get_interaction,
    get_report,
    get_topic_by_name,
    get_topics,
    get_visible_post,
    interaction_counts,
    list_enabled_topics,
    list_visible_posts,
)
from schemas.community_schema import CommentCreate, CommentResponse, PageResult, PostResponse, ReportCreate, TopicResponse
from settings.config import get_settings


DEFAULT_TOPIC_NAMES = ["猫咪", "狗狗", "领养故事", "养宠经验"]
IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
VIDEO_TYPES = {"video/mp4": ".mp4"}


async def _post_response(db: AsyncSession, post: Post, current_user_id: int | None = None) -> PostResponse:
    likes, favorites, comments = await interaction_counts(db, post.id)
    liked_by_me = False
    favorited_by_me = False
    following_author = False
    can_delete = False
    if current_user_id is not None:
        liked_by_me = await get_interaction(db, PostLike, current_user_id, post.id) is not None
        favorited_by_me = await get_interaction(db, PostFavorite, current_user_id, post.id) is not None
        following_author = await get_follow(db, current_user_id, post.user_id) is not None
        can_delete = current_user_id == post.user_id
    return PostResponse(
        id=post.id,
        user_id=post.user_id,
        content=post.content,
        status=post.status,
        media=[dict(
            id=m.id, media_type=m.media_type, file_url=m.file_url, mime_type=m.mime_type,
            file_size=m.file_size, sort_order=m.sort_order
        ) for m in post.media],
        topics=[TopicResponse(id=t.id, name=t.name) for t in post.topics],
        like_count=likes,
        favorite_count=favorites,
        comment_count=comments,
        liked_by_me=liked_by_me,
        favorited_by_me=favorited_by_me,
        following_author=following_author,
        can_delete=can_delete,
        created_at=post.created_at,
    )


def _parse_topic_ids(raw: str | None) -> list[int]:
    if not raw:
        return []
    try:
        values = json.loads(raw)
        ids = [int(value) for value in values]
    except (ValueError, TypeError, json.JSONDecodeError):
        raise bad_request("topic_ids must be a JSON integer array")
    if len(ids) != len(set(ids)):
        raise bad_request("Duplicate topic id")
    return ids


def _parse_topic_names(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        values = json.loads(raw)
        names = [str(value).strip() for value in values if str(value).strip()]
    except (TypeError, json.JSONDecodeError):
        raise bad_request("topic_names must be a JSON string array")
    if len(names) != len(set(names)):
        raise bad_request("Duplicate topic name")
    return names


async def create_post(
    db: AsyncSession,
    user_id: int,
    content: str | None,
    topic_ids_raw: str | None,
    files: list[UploadFile],
    topic_names_raw: str | None = None,
) -> PostResponse:
    content = content.strip() if content else None
    if not content and not files:
        raise bad_request("Post content or media is required")
    images = [f for f in files if f.content_type in IMAGE_TYPES]
    videos = [f for f in files if f.content_type in VIDEO_TYPES]
    if len(files) > 9 or (videos and (len(videos) != 1 or len(files) != 1)):
        raise bad_request("Use up to 9 images or one MP4 video")
    if len(images) + len(videos) != len(files):
        raise bad_request("Unsupported media type")
    for upload in files:
        expected = (IMAGE_TYPES | VIDEO_TYPES)[upload.content_type]
        if Path(upload.filename or "").suffix.lower() != expected:
            raise bad_request("Media extension does not match MIME type")
    topic_ids = _parse_topic_ids(topic_ids_raw)
    topic_names = _parse_topic_names(topic_names_raw)
    topics = await get_topics(db, topic_ids) if topic_ids else []
    if len(topics) != len(topic_ids):
        raise bad_request("Topic not found or disabled")
    if topic_names:
        available_topics = await ensure_topics(db, topic_names)
        topic_by_name = {topic.name: topic for topic in available_topics}
        missing_names = [name for name in topic_names if name not in topic_by_name]
        if missing_names:
            raise bad_request("Topic not found or disabled")
        topics.extend(topic_by_name[name] for name in topic_names)
    topics = list({topic.id: topic for topic in topics}.values())

    settings = get_settings()
    directory = settings.public_asset_path / "community" / str(user_id)
    directory.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []
    post = Post(user_id=user_id, content=content, status=PostStatus.VISIBLE.value, topics=topics)
    try:
        for index, upload in enumerate(files):
            limit = settings.max_upload_size_mb * 1024 * 1024
            data = await upload.read(limit + 1)
            if not data or len(data) > limit:
                raise bad_request("Media file is empty or too large")
            extension = (IMAGE_TYPES | VIDEO_TYPES)[upload.content_type]
            path = directory / f"{uuid4().hex}{extension}"
            path.write_bytes(data)
            saved_paths.append(path)
            post.media.append(PostMedia(
                media_type="image" if upload.content_type in IMAGE_TYPES else "video",
                file_url=f"/generated/community/{user_id}/{path.name}",
                mime_type=upload.content_type,
                file_size=len(data),
                sort_order=index,
            ))
        db.add(post)
        await db.commit()
        await db.refresh(post)
        return await _post_response(db, post, user_id)
    except Exception:
        await db.rollback()
        for path in saved_paths:
            path.unlink(missing_ok=True)
        raise


async def get_posts(
    db: AsyncSession,
    page: int,
    page_size: int,
    current_user_id: int | None = None,
    topic_id: int | None = None,
    topic_name: str | None = None,
    topic_scope: str | None = None,
    sort: str = "latest",
) -> list[PostResponse]:
    if topic_id is None and topic_name:
        topic = await get_topic_by_name(db, topic_name.strip())
        if topic is None:
            return []
        topic_id = topic.id
    exclude_topic_names = DEFAULT_TOPIC_NAMES if topic_scope == "other" else None
    return [
        await _post_response(db, post, current_user_id)
        for post in await list_visible_posts(
            db,
            page,
            page_size,
            topic_id,
            exclude_topic_names=exclude_topic_names,
            sort=sort if sort == "recommend" else "latest",
        )
    ]


async def get_enabled_topics(db: AsyncSession) -> list[TopicResponse]:
    topics = await ensure_topics(db, DEFAULT_TOPIC_NAMES)
    return [TopicResponse.model_validate(topic, from_attributes=True) for topic in topics]


async def get_post(db: AsyncSession, post_id: int, current_user_id: int | None = None) -> PostResponse:
    post = await get_visible_post(db, post_id)
    if post is None:
        raise not_found("Post not found")
    return await _post_response(db, post, current_user_id)


async def delete_post(db: AsyncSession, user_id: int, post_id: int) -> None:
    post = await get_visible_post(db, post_id)
    if post is None:
        raise not_found("Post not found")
    if post.user_id != user_id:
        raise forbidden("Cannot delete another user's post")
    post.status = PostStatus.DELETED.value
    await db.commit()
    _remove_public_media(post)


async def set_interaction(db: AsyncSession, user_id: int, post_id: int, model, enabled: bool) -> None:
    if await get_visible_post(db, post_id) is None:
        raise not_found("Post not found")
    existing = await get_interaction(db, model, user_id, post_id)
    if enabled and existing is None:
        db.add(model(user_id=user_id, post_id=post_id))
    elif not enabled and existing is not None:
        await db.delete(existing)
    await db.commit()


async def add_comment(db: AsyncSession, user_id: int, post_id: int, payload: CommentCreate) -> CommentResponse:
    if await get_visible_post(db, post_id) is None:
        raise not_found("Post not found")
    if payload.parent_id:
        parent = await get_comment(db, payload.parent_id)
        if parent is None or parent.post_id != post_id or parent.is_deleted:
            raise bad_request("Invalid parent comment")
    comment = PostComment(post_id=post_id, user_id=user_id, **payload.model_dump())
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return CommentResponse.model_validate(comment, from_attributes=True)


async def get_comments(db: AsyncSession, post_id: int) -> list[CommentResponse]:
    if await get_visible_post(db, post_id) is None:
        raise not_found("Post not found")
    result = await db.execute(
        select(PostComment).where(PostComment.post_id == post_id, PostComment.is_deleted.is_(False))
        .order_by(PostComment.created_at, PostComment.id)
    )
    return [CommentResponse.model_validate(item, from_attributes=True) for item in result.scalars()]


async def delete_comment(db: AsyncSession, user_id: int, post_id: int, comment_id: int) -> None:
    comment = await get_comment(db, comment_id)
    if comment is None or comment.post_id != post_id or comment.is_deleted:
        raise not_found("Comment not found")
    if comment.user_id != user_id:
        raise forbidden("Cannot delete another user's comment")
    comment.is_deleted = True
    await db.commit()


async def follow_user(db: AsyncSession, follower_id: int, followed_id: int, enabled: bool) -> None:
    if follower_id == followed_id:
        raise bad_request("Cannot follow yourself")
    if await db.get(User, followed_id) is None:
        raise not_found("User not found")
    existing = await get_follow(db, follower_id, followed_id)
    if enabled and existing is None:
        db.add(Follow(follower_id=follower_id, followed_id=followed_id))
    elif not enabled and existing is not None:
        await db.delete(existing)
    await db.commit()


async def create_report(db: AsyncSession, user_id: int, post_id: int, payload: ReportCreate) -> None:
    post = await get_visible_post(db, post_id)
    if post is None:
        raise not_found("Post not found")
    target_id = payload.target_id or post_id
    if payload.target_type == "post" and target_id != post_id:
        raise bad_request("Post target id mismatch")
    if payload.target_type == "comment":
        comment = await get_comment(db, target_id)
        if comment is None or comment.post_id != post_id:
            raise bad_request("Comment does not belong to post")
    existing = await db.scalar(select(Report.id).where(
        Report.reporter_id == user_id, Report.target_type == payload.target_type, Report.target_id == target_id
    ))
    if existing is None:
        db.add(Report(
            reporter_id=user_id, target_type=payload.target_type,
            target_id=target_id, reason=payload.reason
        ))
        await db.commit()


async def list_reports(db: AsyncSession, page: int, page_size: int) -> PageResult:
    total = int((await db.scalar(select(func.count(Report.id)))) or 0)
    rows = (await db.execute(
        select(Report).order_by(Report.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    items = []
    for report in rows:
        target_user: User | None = None
        target_content: str | None = None
        source_area = "community_post" if report.target_type == "post" else "community_comment"
        if report.target_type == "post":
            post = await db.get(Post, report.target_id)
            if post is not None:
                target_user = await db.get(User, post.user_id)
                target_content = post.content
        elif report.target_type == "comment":
            comment = await db.get(PostComment, report.target_id)
            if comment is not None:
                target_user = await db.get(User, comment.user_id)
                target_content = comment.content
        items.append({
            "id": report.id,
            "reporter_id": report.reporter_id,
            "target_type": report.target_type,
            "target_id": report.target_id,
            "source_area": source_area,
            "target_user_id": target_user.id if target_user else None,
            "target_user_nickname": target_user.nickname if target_user else None,
            "target_user_phone": target_user.phone if target_user else None,
            "target_content": target_content,
            "reason": report.reason,
            "status": report.status,
            "action": report.action,
            "resolution_reason": report.resolution_reason,
            "resolved_by": report.resolved_by,
        })
    return PageResult(
        items=items,
        total=total, page=page, page_size=page_size
    )


async def resolve_report(
    db: AsyncSession,
    report_id: int,
    action: str,
    reason: str | None,
    admin_id: int,
    *,
    commit: bool = True,
) -> None:
    if action not in {"dismiss", "take_down"}:
        raise bad_request("Unsupported report action")
    report = await get_report(db, report_id, lock=True)
    if report is None:
        raise not_found("Report not found")
    if report.status == "resolved":
        raise conflict("Report already resolved")
    if action == "take_down" and report.target_type == "post":
        await take_down_post(db, report.target_id, reason, admin_id, commit=False)
    report.status = "resolved"
    report.action = action
    report.resolution_reason = reason
    report.resolved_by = admin_id
    if commit:
        await db.commit()
    else:
        await db.flush()
    if commit and action == "take_down" and report.target_type == "post":
        post = await db.get(Post, report.target_id)
        if post is not None:
            _remove_public_media(post)


async def take_down_post(
    db: AsyncSession, post_id: int, reason: str | None, admin_id: int, commit: bool = True
) -> None:
    post = await db.get(Post, post_id)
    if post is None:
        raise not_found("Post not found")
    if post.status == PostStatus.TAKEN_DOWN.value:
        return
    post.status = PostStatus.TAKEN_DOWN.value
    post.moderation_reason = reason
    if commit:
        await db.commit()
        _remove_public_media(post)


def _remove_public_media(post: Post) -> None:
    root = get_settings().public_asset_path.resolve()
    for media in post.media:
        relative = PurePosixPath(media.file_url.removeprefix("/generated/"))
        path = root.joinpath(*relative.parts).resolve()
        if path.is_relative_to(root):
            path.unlink(missing_ok=True)


async def purge_post_media(db: AsyncSession, post_id: int) -> None:
    post = await db.get(Post, post_id)
    if post is not None:
        _remove_public_media(post)
