"""Configuration resolution for doubao-speech.

Precedence (highest wins):

1. Keyword arguments passed to the public API.
2. Environment variables.
3. ``~/.doubao-speech/config.yaml`` (optional; absent → skipped silently).
4. Built-in defaults.

The resolver is intentionally isolated from network code so it can be
unit-tested without mocking WebSockets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from ._logging import redact_secret
from .exceptions import DoubaoConfigError

#: Default ``~/.doubao-speech/config.yaml`` location. Override via
#: :envvar:`DOUBAO_SPEECH_CONFIG` for test isolation.
DEFAULT_CONFIG_PATH = Path.home() / ".doubao-speech" / "config.yaml"

#: Default speaker voice (Chinese female, warm mid-range).
DEFAULT_SPEAKER = "zh_female_vv_uranus_bigtts"

#: Default audio format produced by the server.
DEFAULT_AUDIO_FORMAT = "mp3"

#: Default sample rate.
DEFAULT_SAMPLE_RATE = 24000

_ENV_APP_ID = ("VOLCENGINE_APP_ID", "DOUBAO_APP_ID")
_ENV_ACCESS_TOKEN = ("VOLCENGINE_ACCESS_TOKEN", "DOUBAO_ACCESS_TOKEN")
_ENV_API_KEY = ("DOUBAO_API_KEY",)
_ENV_RESOURCE_ID = ("VOLCENGINE_RESOURCE_ID", "DOUBAO_RESOURCE_ID")


@dataclass(frozen=True)
class DoubaoConfig:
    """Resolved, ready-to-use configuration for a synthesis call.

    Authentication requires either ``api_key`` or the legacy ``app_id`` and
    ``access_token`` pair. ``speaker``,
    ``audio_format``, and ``sample_rate`` have safe defaults. ``resource_id``
    is optional; Volcengine uses a default resource for seed-tts-2.0 when
    omitted.

    Callers should prefer :meth:`resolve` over constructing instances by
    hand — it applies the full precedence rules and validates credentials.
    """

    app_id: str | None = None
    access_token: str | None = None
    speaker: str = DEFAULT_SPEAKER
    audio_format: str = DEFAULT_AUDIO_FORMAT
    sample_rate: int = DEFAULT_SAMPLE_RATE
    resource_id: str | None = None
    # free-form extras survive config → request mapping unchanged
    extras: dict[str, Any] = field(default_factory=dict)
    # Added after legacy fields to preserve positional-constructor compatibility.
    api_key: str | None = None

    def __repr__(self) -> str:  # safe repr — never leaks credentials
        return (
            "DoubaoConfig("
            f"app_id={redact_secret(self.app_id)!r}, "
            f"access_token={redact_secret(self.access_token)!r}, "
            f"api_key={redact_secret(self.api_key)!r}, "
            f"speaker={self.speaker!r}, "
            f"audio_format={self.audio_format!r}, "
            f"sample_rate={self.sample_rate}, "
            f"resource_id={self.resource_id!r})"
        )

    # ------------------------------------------------------------------
    # resolve
    # ------------------------------------------------------------------
    @classmethod
    def resolve(
        cls,
        *,
        app_id: str | None = None,
        access_token: str | None = None,
        api_key: str | None = None,
        speaker: str | None = None,
        audio_format: str | None = None,
        sample_rate: int | None = None,
        resource_id: str | None = None,
        config_path: Path | None = None,
        env: dict[str, str] | None = None,
        **extras: Any,
    ) -> DoubaoConfig:
        """Resolve effective configuration from explicit args, env, and file.

        Parameters
        ----------
        config_path :
            Override the config-file search location. Use this in tests.
        env :
            Mapping treated as ``os.environ``. Defaults to the real env.
        """
        env_map = env if env is not None else dict(os.environ)
        config_path = config_path or Path(
            env_map.get("DOUBAO_SPEECH_CONFIG", str(DEFAULT_CONFIG_PATH))
        )
        file_cfg = _load_file_config(config_path)

        def pick(
            kw: Any,
            env_keys: tuple[str, ...] | None,
            file_key: str,
            default: Any,
        ) -> Any:
            if kw is not None:
                return kw
            if env_keys:
                for key in env_keys:
                    value = env_map.get(key)
                    if value:
                        return value
            if file_key in file_cfg:
                return file_cfg[file_key]
            return default

        def first_env(keys: tuple[str, ...]) -> Any:
            for key in keys:
                value = env_map.get(key)
                if value:
                    return value
            return None

        explicit_legacy = app_id is not None or access_token is not None
        env_api_key = first_env(_ENV_API_KEY)
        env_app_id = first_env(_ENV_APP_ID)
        env_access_token = first_env(_ENV_ACCESS_TOKEN)

        if api_key:
            resolved_api_key = api_key
            resolved_app_id = None
            resolved_token = None
        elif explicit_legacy:
            resolved_api_key = None
            resolved_app_id = pick(app_id, _ENV_APP_ID, "app_id", None)
            resolved_token = pick(access_token, _ENV_ACCESS_TOKEN, "access_token", None)
        elif env_api_key:
            resolved_api_key = env_api_key
            resolved_app_id = None
            resolved_token = None
        elif env_app_id or env_access_token:
            resolved_api_key = None
            resolved_app_id = env_app_id or file_cfg.get("app_id")
            resolved_token = env_access_token or file_cfg.get("access_token")
        elif file_cfg.get("api_key"):
            resolved_api_key = file_cfg["api_key"]
            resolved_app_id = None
            resolved_token = None
        else:
            resolved_api_key = None
            resolved_app_id = file_cfg.get("app_id")
            resolved_token = file_cfg.get("access_token")

        if not resolved_api_key and not resolved_app_id:
            raise DoubaoConfigError(
                "Missing credentials. Pass api_key=..., set DOUBAO_API_KEY, or provide "
                "legacy app_id/access_token credentials."
            )
        if not resolved_api_key and not resolved_token:
            raise DoubaoConfigError(
                "Missing access_token. Pass access_token=..., set "
                "VOLCENGINE_ACCESS_TOKEN, or add access_token to "
                "~/.doubao-speech/config.yaml."
            )

        return cls(
            app_id=str(resolved_app_id) if resolved_app_id else None,
            access_token=str(resolved_token) if resolved_token else None,
            api_key=str(resolved_api_key) if resolved_api_key else None,
            speaker=pick(speaker, None, "speaker", DEFAULT_SPEAKER),
            audio_format=pick(audio_format, None, "audio_format", DEFAULT_AUDIO_FORMAT),
            sample_rate=int(pick(sample_rate, None, "sample_rate", DEFAULT_SAMPLE_RATE)),
            resource_id=pick(resource_id, _ENV_RESOURCE_ID, "resource_id", None),
            extras={**file_cfg.get("extras", {}), **extras},
        )

    def merge(self, **overrides: Any) -> DoubaoConfig:
        """Return a new :class:`DoubaoConfig` with selected fields replaced."""
        cleaned = {k: v for k, v in overrides.items() if v is not None}
        extras = cleaned.pop("extras", None)
        cfg = replace(self, **cleaned)
        if extras:
            cfg = replace(cfg, extras={**self.extras, **extras})
        return cfg


def _load_file_config(path: Path) -> dict[str, Any]:
    """Load ``~/.doubao-speech/config.yaml`` if present.

    - Missing file → ``{}`` (silent).
    - Empty file → ``{}``.
    - Invalid YAML → :class:`DoubaoConfigError` (loud, not silent).
    - Non-mapping YAML → :class:`DoubaoConfigError`.
    """
    if not path.is_file():
        return {}

    try:
        import yaml  # local import keeps package import cheap
    except ImportError as exc:  # pragma: no cover — pyyaml is a hard dep
        raise DoubaoConfigError("PyYAML is required to load ~/.doubao-speech/config.yaml") from exc

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DoubaoConfigError(f"Cannot read config file {path}: {exc}") from exc

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise DoubaoConfigError(f"Malformed YAML in {path}: {exc}") from exc

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise DoubaoConfigError(
            f"Config file {path} must contain a YAML mapping, got {type(data).__name__}"
        )
    return data
