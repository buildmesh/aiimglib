"""End-to-end tests for image API endpoints."""
from __future__ import annotations

import io
import json
from datetime import datetime, timezone

import pytest

from app.config import settings


def upload_media(
    client,
    *,
    prompt_text: str,
    tags=None,
    rating=None,
    media_type="image",
    prompt_meta=None,
    thumbnail=True,
):
    body = {
        "prompt_text": prompt_text,
        "tags": json.dumps(tags or []),
        "rating": str(rating) if rating is not None else "",
        "media_type": media_type,
        "prompt_meta": json.dumps(prompt_meta) if prompt_meta is not None else "",
    }
    body["captured_at"] = datetime.now(tz=timezone.utc).isoformat()
    files = {
        "media_file": (
            "sample.png" if media_type == "image" else "clip.mp4",
            io.BytesIO(b"fake-media-bytes"),
            "image/png" if media_type == "image" else "video/mp4",
        ),
    }
    if media_type == "video" and thumbnail:
        files["thumbnail_file"] = (
            "thumb.png",
            io.BytesIO(b"thumb-bytes"),
            "image/png",
        )
    response = client.post("/api/images", data=body, files=files)
    assert response.status_code == 201, response.text
    return response.json()


def test_upload_list_update_and_delete_flow(api_client):
    created = upload_media(
        api_client,
        prompt_text="Spaceship launching from Mars",
        tags=["Space", "SciFi"],
        rating=5.0,
        prompt_meta=[{"id": "seed-role"}, "Spaceship launching from Mars"],
    )
    path = settings.images_dir / created["file_name"]
    assert path.exists()

    response = api_client.get(
        "/api/images",
        params={"q": "space", "tags": "scifi", "rating_min": 4.0, "rating_max": 5.0},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == created["id"]

    update_resp = api_client.put(
        f"/api/images/{created['id']}",
        json={"notes": "updated-notes", "tags": ["new", "space"]},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["notes"] == "updated-notes"
    assert {tag["name"] for tag in updated["tags"]} == {"new", "space"}

    replace_resp = api_client.post(
        f"/api/images/{created['id']}/file",
        files={"media_file": ("new.png", io.BytesIO(b"new-bytes"), "image/png")},
    )
    assert replace_resp.status_code == 200
    replaced = replace_resp.json()
    assert replaced["file_name"] != created["file_name"]
    new_path = settings.images_dir / replaced["file_name"]
    assert new_path.exists()

    delete_resp = api_client.delete(f"/api/images/{created['id']}")
    assert delete_resp.status_code == 204
    assert not new_path.exists()


def test_upload_invalid_captured_at_returns_422(api_client):
    files = {
        "media_file": ("sample.png", io.BytesIO(b"fake-image-bytes"), "image/png"),
    }
    data = {
        "prompt_text": "Invalid timestamp test",
        "captured_at": "not-a-date",
        "tags": json.dumps([]),
    }

    response = api_client.post("/api/images", data=data, files=files)

    assert response.status_code == 422
    assert response.json()["detail"] == "captured_at must be ISO-8601 datetime"
    assert not any(settings.images_dir.iterdir())


def test_upload_video_requires_thumbnail(api_client):
    body = {
        "prompt_text": "Video without thumbnail",
        "media_type": "video",
        "tags": json.dumps([]),
    }
    files = {
        "media_file": ("clip.mp4", io.BytesIO(b"video"), "video/mp4"),
    }

    response = api_client.post("/api/images", data=body, files=files)

    assert response.status_code == 400
    assert "thumbnail" in response.json()["detail"].lower()


def test_list_filters_support_decimal_ratings_and_media_type(api_client):
    video = upload_media(
        api_client,
        prompt_text="Video entry",
        media_type="video",
        thumbnail=True,
        rating=3.7,
    )
    upload_media(api_client, prompt_text="Image entry", rating=4.9)

    response = api_client.get(
        "/api/images",
        params={"rating_min": 3.5, "rating_max": 4.0, "media_type": "video"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == video["id"]


def test_detail_endpoint_returns_prompt_meta_and_thumbnail(api_client):
    created = upload_media(
        api_client,
        prompt_text="Prompt meta detail",
        prompt_meta=[{"id": "seed"}, "Prompt meta detail"],
    )

    response = api_client.get(f"/api/images/{created['id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["prompt_meta"] == [{"id": "seed"}, "Prompt meta detail"]
    assert payload["thumbnail_file"] is None


def test_detail_endpoint_includes_dependents(api_client):
    parent = upload_media(api_client, prompt_text="Parent image")
    child = upload_media(
        api_client,
        prompt_text="Child referencing parent",
        prompt_meta=[{"id": parent["id"]}, "Child referencing parent"],
    )

    response = api_client.get(f"/api/images/{parent['id']}")

    assert response.status_code == 200
    payload = response.json()
    dependents = payload.get("dependents", [])
    assert len(dependents) == 1
    dependent = dependents[0]
    assert dependent["id"] == child["id"]
    assert dependent["file_name"] == child["file_name"]
    assert dependent["media_type"] == "image"
