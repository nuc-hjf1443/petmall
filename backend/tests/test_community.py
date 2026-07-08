import pytest
from pathlib import Path
from sqlalchemy import select

from models.audit import AuditLog
from models.user import User
from tests.test_order_payment import auth, register


pytestmark = pytest.mark.asyncio


async def test_post_media_interactions_and_permissions(test_context, strong_password, tmp_path):
    from settings.config import get_settings

    settings = get_settings()
    original = settings.generated_asset_dir
    settings.generated_asset_dir = str(tmp_path)
    try:
        client = test_context["client"]
        token_a = await register(client, test_context["cache"], "13930000001", strong_password)
        token_b = await register(client, test_context["cache"], "13930000002", strong_password)
        post = await client.post(
            "/posts",
            headers=auth(token_a),
            data={"content": "hello pets"},
            files={"files": ("pet.jpg", b"fake-image", "image/jpeg")},
        )
        assert post.status_code == 200, post.text
        post_id = post.json()["id"]
        author_id = post.json()["user_id"]
        assert post.json()["can_delete"] is True
        media_url = post.json()["media"][0]["file_url"]
        assert ".." not in media_url
        media_path = settings.public_asset_path / Path(
            media_url.removeprefix("/generated/")
        )
        assert media_path.exists()

        assert (await client.post(f"/posts/{post_id}/likes", headers=auth(token_b))).status_code == 200
        assert (await client.post(f"/posts/{post_id}/likes", headers=auth(token_b))).status_code == 200
        anonymous_detail = await client.get(f"/posts/{post_id}")
        assert anonymous_detail.json()["like_count"] == 1
        assert anonymous_detail.json()["liked_by_me"] is False
        detail = await client.get(f"/posts/{post_id}", headers=auth(token_b))
        assert detail.json()["liked_by_me"] is True
        assert detail.json()["can_delete"] is False
        assert (await client.post(f"/posts/{post_id}/favorites", headers=auth(token_b))).status_code == 200
        assert (await client.post(f"/posts/{post_id}/favorites", headers=auth(token_b))).status_code == 200
        detail = await client.get(f"/posts/{post_id}", headers=auth(token_b))
        assert detail.json()["favorite_count"] == 1
        assert detail.json()["favorited_by_me"] is True
        assert (await client.delete(f"/posts/{post_id}/likes", headers=auth(token_b))).status_code == 200
        assert (await client.delete(f"/posts/{post_id}/favorites", headers=auth(token_b))).status_code == 200
        detail = await client.get(f"/posts/{post_id}", headers=auth(token_b))
        assert detail.json()["liked_by_me"] is False
        assert detail.json()["favorited_by_me"] is False
        assert (await client.delete(f"/posts/{post_id}", headers=auth(token_b))).status_code == 403
        assert (await client.post("/users/2/follow", headers=auth(token_b))).status_code == 400
        assert (await client.post(f"/users/{author_id}/follow", headers=auth(token_b))).status_code == 200
        detail = await client.get(f"/posts/{post_id}", headers=auth(token_b))
        assert detail.json()["following_author"] is True
        assert (await client.delete(f"/users/{author_id}/follow", headers=auth(token_b))).status_code == 200
        list_result = await client.get("/posts", headers=auth(token_b))
        assert list_result.json()[0]["following_author"] is False
        report = await client.post(
            f"/posts/{post_id}/reports", headers=auth(token_b),
            json={"target_type": "post", "reason": "review this"},
        )
        assert report.status_code == 200
        bad_media = await client.post(
            "/posts", headers=auth(token_a), data={"content": "bad"},
            files={"files": ("pet.exe", b"bad", "image/jpeg")},
        )
        assert bad_media.status_code == 400
        assert (await client.delete(f"/posts/{post_id}", headers=auth(token_a))).status_code == 200
        assert not media_path.exists()
    finally:
        settings.generated_asset_dir = original


async def test_admin_report_resolution_state_and_duplicate_guard(test_context, strong_password):
    client = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]

    author_token = await register(client, cache, "13930000011", strong_password)
    reporter_token = await register(client, cache, "13930000012", strong_password)
    admin_token = await register(client, cache, "13930000013", strong_password)
    async with session_factory() as db:
        admin = (await db.execute(select(User).where(User.phone == "13930000013"))).scalar_one()
        admin.is_admin = True
        author = (await db.execute(select(User).where(User.phone == "13930000011"))).scalar_one()
        author.nickname = "Reported Author"
        await db.commit()

    post = await client.post(
        "/posts",
        headers=auth(author_token),
        data={"content": "unsafe community post"},
    )
    assert post.status_code == 200, post.text
    post_id = post.json()["id"]

    report = await client.post(
        f"/posts/{post_id}/reports",
        headers=auth(reporter_token),
        json={"target_type": "post", "reason": "review this"},
    )
    assert report.status_code == 200, report.text

    reports = await client.get("/admin/reports", headers=auth(admin_token))
    assert reports.status_code == 200, reports.text
    report_item = reports.json()["items"][0]
    assert report_item["status"] == "pending"
    assert report_item["action"] is None
    assert report_item["resolution_reason"] is None
    assert report_item["resolved_by"] is None
    assert report_item["source_area"] == "community_post"
    assert report_item["target_user_nickname"] == "Reported Author"
    assert report_item["target_user_phone"] == "13930000011"
    assert report_item["target_content"] == "unsafe community post"

    resolved = await client.post(
        f"/admin/reports/{report_item['id']}/resolve",
        headers=auth(admin_token),
        json={"action": "take_down", "reason": "violates community rules"},
    )
    assert resolved.status_code == 200, resolved.text

    duplicate = await client.post(
        f"/admin/reports/{report_item['id']}/resolve",
        headers=auth(admin_token),
        json={"action": "dismiss", "reason": "second action"},
    )
    assert duplicate.status_code == 409

    reports_after = await client.get("/admin/reports", headers=auth(admin_token))
    assert reports_after.status_code == 200, reports_after.text
    resolved_item = reports_after.json()["items"][0]
    assert resolved_item["status"] == "resolved"
    assert resolved_item["action"] == "take_down"
    assert resolved_item["resolution_reason"] == "violates community rules"
    assert resolved_item["resolved_by"] is not None

    hidden = await client.get(f"/posts/{post_id}")
    assert hidden.status_code == 404

    async with session_factory() as db:
        logs = (await db.execute(
            select(AuditLog).where(
                AuditLog.target_type == "report",
                AuditLog.target_id == report_item["id"],
            )
        )).scalars().all()
    assert len(logs) == 1
    assert logs[0].action == "take_down"


async def test_comment_reply_parent_validation(test_context, strong_password):
    client = test_context["client"]
    cache = test_context["cache"]
    token_a = await register(client, cache, "13930000021", strong_password)
    token_b = await register(client, cache, "13930000022", strong_password)

    post_a = await client.post("/posts", headers=auth(token_a), data={"content": "first"})
    post_b = await client.post("/posts", headers=auth(token_a), data={"content": "second"})
    assert post_a.status_code == 200, post_a.text
    assert post_b.status_code == 200, post_b.text
    post_a_id = post_a.json()["id"]
    post_b_id = post_b.json()["id"]

    parent = await client.post(
        f"/posts/{post_a_id}/comments",
        headers=auth(token_b),
        json={"content": "parent comment"},
    )
    assert parent.status_code == 200, parent.text
    parent_id = parent.json()["id"]

    reply = await client.post(
        f"/posts/{post_a_id}/comments",
        headers=auth(token_a),
        json={"content": "reply comment", "parent_id": parent_id},
    )
    assert reply.status_code == 200, reply.text
    assert reply.json()["parent_id"] == parent_id

    cross_post = await client.post(
        f"/posts/{post_b_id}/comments",
        headers=auth(token_a),
        json={"content": "bad reply", "parent_id": parent_id},
    )
    assert cross_post.status_code == 400

    await client.delete(f"/posts/{post_a_id}/comments/{parent_id}", headers=auth(token_b))
    deleted_parent = await client.post(
        f"/posts/{post_a_id}/comments",
        headers=auth(token_a),
        json={"content": "bad reply after delete", "parent_id": parent_id},
    )
    assert deleted_parent.status_code == 400


async def test_post_list_can_filter_by_topic(test_context, strong_password):
    client = test_context["client"]
    cache = test_context["cache"]
    token = await register(client, cache, "13930000031", strong_password)
    liker_token = await register(client, cache, "13930000032", strong_password)

    topics = await client.get("/topics")
    assert topics.status_code == 200, topics.text
    cat_topic = next(item for item in topics.json() if item["name"] == "猫咪")
    dog_topic = next(item for item in topics.json() if item["name"] == "狗狗")

    cat_post = await client.post(
        "/posts",
        headers=auth(token),
        data={"content": "cat post", "topic_ids": f"[{cat_topic['id']}]"},
    )
    dog_post = await client.post(
        "/posts",
        headers=auth(token),
        data={"content": "dog post", "topic_ids": f"[{dog_topic['id']}]"},
    )
    other_post = await client.post(
        "/posts",
        headers=auth(token),
        data={"content": "other post"},
    )
    name_post = await client.post(
        "/posts",
        headers=auth(token),
        data={"content": "name topic post", "topic_names": '["养宠经验"]'},
    )
    assert cat_post.status_code == 200, cat_post.text
    assert dog_post.status_code == 200, dog_post.text
    assert other_post.status_code == 200, other_post.text
    assert name_post.status_code == 200, name_post.text

    cat_posts = await client.get(f"/posts?topic_id={cat_topic['id']}")
    assert cat_posts.status_code == 200, cat_posts.text
    assert [item["content"] for item in cat_posts.json()] == ["cat post"]

    name_posts = await client.get("/posts?topic_name=养宠经验")
    assert name_posts.status_code == 200, name_posts.text
    assert [item["content"] for item in name_posts.json()] == ["name topic post"]

    other_posts = await client.get("/posts?topic_scope=other")
    assert other_posts.status_code == 200, other_posts.text
    assert [item["content"] for item in other_posts.json()] == ["other post"]

    liked = await client.post(f"/posts/{cat_post.json()['id']}/likes", headers=auth(liker_token))
    assert liked.status_code == 200, liked.text

    latest_posts = await client.get("/posts?sort=latest")
    assert latest_posts.status_code == 200, latest_posts.text
    assert latest_posts.json()[0]["content"] == "name topic post"

    recommended_posts = await client.get("/posts?sort=recommend")
    assert recommended_posts.status_code == 200, recommended_posts.text
    assert recommended_posts.json()[0]["content"] == "cat post"

    all_posts = await client.get("/posts")
    assert all_posts.status_code == 200, all_posts.text
    assert {item["content"] for item in all_posts.json()} >= {"cat post", "dog post", "other post", "name topic post"}
