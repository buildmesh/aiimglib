"""End-to-end tests for image API endpoints."""
from __future__ import annotations

import io
import json
from datetime import datetime, timezone

from app.config import settings


def upload_image(client, prompt_text: str, *, tags=None, rating=None):
    body = {
        "prompt_text": prompt_text,
        "tags": json.dumps(tags or []),
        "rating": str(rating) if rating is not None else "",
    }
    body["captured_at"] = datetime.now(tz=timezone.utc).isoformat()
    files = {
        "image_file": ("sample.png", io.BytesIO(b"fake-image-bytes"), "image/png"),
    }
    response = client.post("/api/images", data=body, files=files)
    assert response.status_code == 201, response.text
    return response.json()


def test_upload_list_update_and_delete_flow(api_client):
    created = upload_image(
        api_client,
        "Spaceship launching from Mars",
        tags=["Space", "SciFi"],
        rating=5,
    )
    path = settings.images_dir / created["file_name"]
    assert path.exists()

    response = api_client.get(
        "/api/images",
        params={"q": "space", "tags": "scifi", "rating_min": 4},
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
        files={"image_file": ("new.png", io.BytesIO(b"new-bytes"), "image/png")},
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
        "image_file": ("sample.png", io.BytesIO(b"fake-image-bytes"), "image/png"),
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
