"""Tests for the legacy JSON import helpers."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from scripts import import_legacy_json as importer


def test_load_entries_handles_root_image_list(tmp_path):
    payload = {
        "image": [
            {
                "file": "foo.png",
                "prompt": "hello world",
                "date": "2024-01-01T00:00:00Z",
            }
        ]
    }
    json_path = tmp_path / "legacy.json"
    json_path.write_text(importer.json.dumps(payload))

    entries = importer.load_entries(json_path)

    assert isinstance(entries, list)
    assert entries[0]["file"] == "foo.png"


def test_convert_entry_maps_prompt_and_date():
    legacy = {
        "file": "bar.png",
        "prompt": [{"id": "base"}, "refined prompt"],
        "date": "2024-03-15T12:34:56Z",
        "ai_model": "sdxl",
        "notes": "note",
        "tags": ["SciFi", "scifi"],
        "rating": 5,
    }

    converted = importer.convert_entry(legacy)

    assert converted["file_name"] == "bar.png"
    assert converted["prompt_text"] == "refined prompt"
    assert converted["prompt_meta"] == legacy["prompt"]
    assert converted["captured_at"] == datetime(2024, 3, 15, 12, 34, 56, tzinfo=timezone.utc)
    assert sorted(converted["tags"]) == ["scifi"]
