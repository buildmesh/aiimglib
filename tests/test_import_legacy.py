"""Tests for the legacy JSON import helpers."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app import models
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
        "id": "legacy-source",
        "file": "bar.png",
        "prompt": [{"id": "base"}, "refined prompt"],
        "date": "2024-03-15T12:34:56Z",
        "ai_model": "sdxl",
        "notes": "note",
        "tags": ["SciFi", "scifi"],
        "rating": 5,
    }

    converted = importer.convert_entry(legacy)

    assert converted.payload["file_name"] == "bar.png"
    assert converted.payload["prompt_text"] == "refined prompt"
    assert converted.payload["prompt_meta"] == legacy["prompt"]
    assert converted.payload["captured_at"] == datetime(2024, 3, 15, 12, 34, 56, tzinfo=timezone.utc)
    assert sorted(converted.tags) == ["scifi"]
    assert converted.legacy_id == "legacy-source"
    assert converted.reference_dicts == [{"id": "base"}]


def test_convert_entry_normalizes_decimal_ratings_and_media_type():
    legacy = {
        "id": "clip-id",
        "file": "clip.MP4",
        "prompt": "short prompt",
        "rating": "4.7",
        "thumbnail_file": "clip-thumb.PNG",
    }

    converted = importer.convert_entry(legacy)

    assert converted.payload["media_type"] == models.MediaType.VIDEO
    assert converted.payload["thumbnail_file"] == "clip-thumb.PNG"
    assert pytest.approx(converted.payload["rating"], rel=0.001) == 4.7


def test_convert_entry_rejects_prompt_list_without_trailing_text():
    legacy = {
        "file": "broken.png",
        "prompt": [{"id": "abc"}],
    }

    with pytest.raises(ValueError):
        importer.convert_entry(legacy)


def test_convert_entry_rejects_prompt_list_with_invalid_reference_shape():
    legacy = {
        "file": "broken2.png",
        "prompt": [{"id": "abc"}, {"not_id": "nope"}, "prompt"],
    }

    with pytest.raises(ValueError):
        importer.convert_entry(legacy)


def test_convert_entry_video_without_thumbnail_or_reference_errors():
    legacy = {
        "file": "clip.mp4",
        "prompt": "video prompt",
    }

    with pytest.raises(ValueError):
        importer.convert_entry(legacy)


def create_test_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_apply_reference_updates_sets_prompt_meta_and_thumbnail():
    with create_test_session() as session:
        base = models.Image(file_name="base.png", prompt_text="base text", thumbnail_file="base-thumb.png")
        session.add(base)
        session.commit()
        session.refresh(base)

        derived = models.Image(
            file_name="derived.png",
            prompt_text="derived prompt",
            prompt_meta=[{"id": "legacy-base"}, "derived prompt"],
        )
        session.add(derived)
        session.commit()
        session.refresh(derived)

        legacy_lookup = {
            "legacy-base": {
                "id": base.id,
                "file_name": base.file_name,
                "thumbnail_file": base.thumbnail_file,
            },
            "legacy-derived": {
                "id": derived.id,
                "file_name": derived.file_name,
                "thumbnail_file": derived.thumbnail_file,
            },
        }
        records = [
            importer.ImportedRecord(
                image_id=derived.id,
                legacy_id="legacy-derived",
                reference_dicts=[{"id": "legacy-base"}],
                has_explicit_thumbnail=False,
                media_type=models.MediaType.IMAGE,
            )
        ]

        importer._apply_reference_updates(session, records, legacy_lookup)

        updated = session.get(models.Image, derived.id)
        assert updated is not None
        assert updated.prompt_meta[0]["id"] == base.id
        assert updated.prompt_meta[-1] == "derived prompt"
        assert updated.thumbnail_file == "base-thumb.png"
        assert legacy_lookup["legacy-derived"]["thumbnail_file"] == "base-thumb.png"
