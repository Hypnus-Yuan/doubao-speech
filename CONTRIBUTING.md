# Contributing to doubao-speech

Thanks for your interest! This project welcomes issues and pull requests.

## Development setup

```bash
git clone https://github.com/Hypnus-Yuan/doubao-speech.git
cd doubao-speech

uv sync --all-extras --group dev
uv run pre-commit install
```

## Common commands

```bash
uv run ruff format .          # format
uv run ruff check . --fix     # lint + autofix
uv run mypy                   # type-check
uv run pytest                 # unit tests only
uv run pytest -m integration  # live-credential suite (needs VOLCENGINE_*)
uv build                      # produce sdist + wheel
```

## Running the integration suite

Integration tests hit the real Volcengine seed-tts-2.0 endpoint. Set
credentials in your shell before running them:

```bash
export VOLCENGINE_APP_ID="..."
export VOLCENGINE_ACCESS_TOKEN="..."
uv run pytest -m integration
```

These are never run in CI for PRs from forks to avoid leaking secrets.

## Pull request checklist

- [ ] `uv run ruff format --check .` clean
- [ ] `uv run ruff check .` clean
- [ ] `uv run mypy` clean
- [ ] `uv run pytest` green (coverage ≥ 85%)
- [ ] New public API documented with a docstring
- [ ] User-visible changes recorded in `CHANGELOG.md`
- [ ] If the change touches credential handling, update `SECURITY.md`

## Project philosophy

- **Top-level import is cheap.** `import doubao_speech` must not pull in
  `websockets`, `yaml`, or anything else with >1 ms cost. Enforced by
  `tests/unit/test_import.py`.
- **Credentials never hit logs in full.** Any new code path that touches
  an access token must go through `_logging.redact_secret`.
- **Synthesis text is private.** Request payloads are logged at length
  only; raw-payload tracing is opt-in via `DOUBAO_SPEECH_TRACE_PAYLOADS=1`.
- **Small public surface.** We'd rather expose one `synthesize()` that
  works than five overlapping abstractions.

## Release process (maintainer)

1. Update `version` in `pyproject.toml`
2. Update `CHANGELOG.md`
3. `git commit -m "Release vX.Y.Z" && git tag vX.Y.Z && git push --tags`
4. Cut a GitHub Release matching the tag → triggers `publish.yml`
5. Verify `pip install doubao-speech==X.Y.Z` in a clean venv

## Code of conduct

Be respectful. See `CODE_OF_CONDUCT.md`.
