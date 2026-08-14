"""Authentication header construction tests."""

from doubao_speech._ws_client import _build_headers, _resolve_credentials


def test_resolve_api_key_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DOUBAO_API_KEY", "env_api_key")
    monkeypatch.delenv("VOLCENGINE_APP_ID", raising=False)
    monkeypatch.delenv("VOLCENGINE_ACCESS_TOKEN", raising=False)

    assert _resolve_credentials(None, None, None) == (None, None, "env_api_key")


def test_explicit_legacy_credentials_override_environment_api_key(monkeypatch) -> None:
    monkeypatch.setenv("DOUBAO_API_KEY", "env_api_key")

    assert _resolve_credentials("legacy_app", "legacy_token", None) == (
        "legacy_app",
        "legacy_token",
        None,
    )


def test_legacy_auth_headers_are_preserved() -> None:
    headers = _build_headers(
        app_id="legacy_app",
        access_token="legacy_token",
        resource_id="legacy_resource",
        request_id="request-id",
    )

    assert headers["X-Api-App-Id"] == "legacy_app"
    assert headers["X-Api-App-Key"] == "legacy_app"
    assert headers["X-Api-Access-Key"] == "legacy_token"
    assert "X-Api-Key" not in headers


def test_api_key_auth_uses_only_new_header() -> None:
    headers = _build_headers(
        app_id=None,
        access_token=None,
        api_key="new_api_key",
        resource_id="volc.seedasr.sauc.duration",
        request_id="request-id",
    )

    assert headers["X-Api-Key"] == "new_api_key"
    assert "X-Api-App-Id" not in headers
    assert "X-Api-App-Key" not in headers
    assert "X-Api-Access-Key" not in headers
