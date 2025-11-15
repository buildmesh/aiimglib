"""Smoke test ensuring the frontend bundle serves HTML."""
from __future__ import annotations


def test_homepage_served(api_client):
    response = api_client.get("/")

    assert response.status_code == 200
    body = response.text.lower()
    assert "ai image" in body
    assert "/api/images" in body
