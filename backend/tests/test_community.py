import pytest
from pathlib import Path

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
        media_url = post.json()["media"][0]["file_url"]
        assert ".." not in media_url
        media_path = settings.public_asset_path / Path(
            media_url.removeprefix("/generated/")
        )
        assert media_path.exists()

        assert (await client.post(f"/posts/{post_id}/likes", headers=auth(token_b))).status_code == 200
        assert (await client.post(f"/posts/{post_id}/likes", headers=auth(token_b))).status_code == 200
        detail = await client.get(f"/posts/{post_id}")
        assert detail.json()["like_count"] == 1
        assert (await client.post(f"/posts/{post_id}/favorites", headers=auth(token_b))).status_code == 200
        assert (await client.post(f"/posts/{post_id}/favorites", headers=auth(token_b))).status_code == 200
        assert (await client.get(f"/posts/{post_id}")).json()["favorite_count"] == 1
        assert (await client.delete(f"/posts/{post_id}", headers=auth(token_b))).status_code == 403
        assert (await client.post("/users/2/follow", headers=auth(token_b))).status_code == 400
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
