from __future__ import annotations

from pathlib import Path

import pytest

from common.config import ConfigError, get_env, get_int_env


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_get_env_required_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI3_MISSING_TEST_VALUE", raising=False)

    with pytest.raises(ConfigError, match="AI3_MISSING_TEST_VALUE"):
        get_env("AI3_MISSING_TEST_VALUE", required=True)


def test_get_int_env_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI3_INT_TEST_VALUE", "not-int")

    with pytest.raises(ConfigError, match="must be an integer"):
        get_int_env("AI3_INT_TEST_VALUE")


def test_get_env_reads_dotenv_when_process_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI3_ENV_FILE", str(FIXTURES / "config.env"))
    monkeypatch.delenv("AI3_DOTENV_VALUE", raising=False)
    monkeypatch.delenv("AI3_QUOTED_VALUE", raising=False)
    monkeypatch.delenv("AI3_EXPORTED_VALUE", raising=False)
    monkeypatch.delenv("AI3_COMMENTED_VALUE", raising=False)
    _clear_dotenv_cache()

    assert get_env("AI3_DOTENV_VALUE") == "from-dotenv"
    assert get_env("AI3_QUOTED_VALUE") == "quoted value"
    assert get_env("AI3_EXPORTED_VALUE") == "exported"
    assert get_env("AI3_COMMENTED_VALUE") == "value"


def test_get_env_process_env_overrides_dotenv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI3_ENV_FILE", str(FIXTURES / "config.env"))
    monkeypatch.setenv("AI3_OVERRIDE_VALUE", "from-env")
    _clear_dotenv_cache()

    assert get_env("AI3_OVERRIDE_VALUE") == "from-env"


def _clear_dotenv_cache() -> None:
    from common import config

    config._dotenv_values.cache_clear()
