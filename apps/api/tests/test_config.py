import pytest

from app import config


def test_validate_runtime_config_requires_token(monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", "")
    with pytest.raises(RuntimeError):
        config.validate_runtime_config()


def test_validate_runtime_config_rejects_bad_scheduler_interval(monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", "token")
    monkeypatch.setattr(config, "CORS_ORIGINS", ["https://app.example.com"])
    monkeypatch.setattr(config, "SCHEDULER_INTERVAL_MINUTES", 0)
    with pytest.raises(RuntimeError):
        config.validate_runtime_config()


def test_validate_runtime_config_allows_wildcard_cors(monkeypatch):
    # Wildcard CORS is allowed (useful for initial deploys without explicit origins set)
    monkeypatch.setattr(config, "JWT_SECRET", "token")
    monkeypatch.setattr(config, "SCHEDULER_INTERVAL_MINUTES", 5)
    monkeypatch.setattr(config, "CORS_ORIGINS", ["*"])
    config.validate_runtime_config()  # should not raise
