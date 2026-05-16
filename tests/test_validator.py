"""Tests for envdrift value format heuristics."""

from envdrift.differ import _looks_like_secret


def test_secret_key_detection():
    assert _looks_like_secret("SECRET_KEY") is True
    assert _looks_like_secret("API_TOKEN") is True
    assert _looks_like_secret("DB_PASSWORD") is True
    assert _looks_like_secret("PRIVATE_KEY") is True
    assert _looks_like_secret("AUTH_CREDENTIAL") is True


def test_non_secret_key():
    assert _looks_like_secret("DB_HOST") is False
    assert _looks_like_secret("PORT") is False
    assert _looks_like_secret("APP_NAME") is False
    assert _looks_like_secret("LOG_LEVEL") is False


def test_empty_key():
    assert _looks_like_secret("") is False
