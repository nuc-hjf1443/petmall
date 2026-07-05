from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class PostStatus(StrEnum):
    VISIBLE = "visible"
    DELETED = "deleted"
    TAKEN_DOWN = "taken_down"


class Post(Base, TimestampMixin):
    __tablename__ = "post"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    content: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default=PostStatus.VISIBLE.value, index=True)
    moderation_reason: Mapped[str | None] = mapped_column(Text)
    media: Mapped[list["PostMedia"]] = relationship(
        back_populates="post", cascade="all, delete-orphan", lazy="selectin", order_by="PostMedia.sort_order"
    )
    topics: Mapped[list["Topic"]] = relationship(
        secondary="post_topic", lazy="selectin", back_populates="posts"
    )


class PostMedia(Base, TimestampMixin):
    __tablename__ = "post_media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id"), index=True)
    media_type: Mapped[str] = mapped_column(String(16))
    file_url: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128))
    file_size: Mapped[int] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer)
    post: Mapped[Post] = relationship(back_populates="media")


class PostComment(Base, TimestampMixin):
    __tablename__ = "post_comment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("post_comment.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class PostLike(Base, TimestampMixin):
    __tablename__ = "post_like"
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_post_like_user_post"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id"), index=True)


class PostFavorite(Base, TimestampMixin):
    __tablename__ = "post_favorite"
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_post_favorite_user_post"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id"), index=True)


class Topic(Base, TimestampMixin):
    __tablename__ = "topic"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    posts: Mapped[list[Post]] = relationship(secondary="post_topic", back_populates="topics")


class PostTopic(Base):
    __tablename__ = "post_topic"
    __table_args__ = (UniqueConstraint("post_id", "topic_id", name="uq_post_topic"),)

    post_id: Mapped[int] = mapped_column(ForeignKey("post.id"), primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topic.id"), primary_key=True)


class Follow(Base, TimestampMixin):
    __tablename__ = "follow"
    __table_args__ = (UniqueConstraint("follower_id", "followed_id", name="uq_follow_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    follower_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    followed_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)


class Report(Base, TimestampMixin):
    __tablename__ = "report"
    __table_args__ = (
        UniqueConstraint("reporter_id", "target_type", "target_id", name="uq_reporter_target"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(32), index=True)
    target_id: Mapped[int] = mapped_column(Integer, index=True)
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    action: Mapped[str | None] = mapped_column(String(32))
    resolution_reason: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
