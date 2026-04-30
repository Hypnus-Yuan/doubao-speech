# Security Policy

## Reporting a vulnerability

If you discover a security issue in `doubao-speech`, **please do not open a
public GitHub issue.** Report it privately instead:

- Email: `hypnus.yuan@gmail.com`
- Or open a **private security advisory** at
  <https://github.com/Hypnus-Yuan/doubao-speech/security/advisories/new>

Please include:

- A description of the issue and its impact.
- Steps to reproduce, ideally as a minimal code sample.
- Affected versions.

You should get an acknowledgement within **72 hours**. Fixes ship as
patch releases on PyPI; credit is given unless you ask to stay anonymous.

## Credential handling

`doubao-speech` touches a sensitive resource: the Volcengine access token.
The package follows these rules — please file an issue if you see any
of them violated:

1. Access tokens are **never logged in full.** `DoubaoConfig.__repr__`
   and CLI `doubao-speech config show` redact tokens to
   ``first4...last4``.
2. Request payloads (including user-provided text) are **only logged
   in full** when the user opts in via
   ``DOUBAO_SPEECH_TRACE_PAYLOADS=1``. Default `DEBUG` logs show payload
   length only.
3. `~/.doubao-speech/config.yaml` is the recommended place for a token;
   the shipped `.gitignore` excludes `.env` files.
4. CI tests that require live credentials are marked
   `@pytest.mark.integration` and are **never** run on PRs from forks.

## If a token leaks

1. Log into the Volcengine console.
2. Navigate to `Speech services → Application management`.
3. Rotate the token on the affected application.
4. Grep your logs for `redact_secret`-style prefixes
   (`first4...last4`) to see whether the token reached third-party
   aggregators.
