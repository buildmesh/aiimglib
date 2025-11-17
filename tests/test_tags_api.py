"""Tests for tag listing endpoint."""
from __future__ import annotations

import io
import json


def upload(client, prompt, tags):
    data = {
        "prompt_text": prompt,
        "tags": json.dumps(tags),
    }
    files = {"media_file": ("a.png", io.BytesIO(b"img"), "image/png")}
    resp = client.post("/api/images", data=data, files=files)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_tag_listing_returns_counts(api_client):
    upload(api_client, "Galaxy view", ["space", "galaxy"])
    upload(api_client, "Another scene", ["space"])

    resp = api_client.get("/api/tags")
    assert resp.status_code == 200
    payload = resp.json()
    counts = {item["name"]: item["count"] for item in payload}
    assert counts["space"] == 2
    assert counts["galaxy"] == 1
