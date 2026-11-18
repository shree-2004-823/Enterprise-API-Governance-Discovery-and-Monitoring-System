# Security Audit

## Scope and method

The initial review was read-only and covered the Flask/MariaDB application source and relevant templates, configuration, and database setup code. The local `.env` file and virtual environment were excluded. After the review, the user authorized fixes for findings 1 and 2. No database changes were made, and no database setup/reset command was run.

The findings below are based on the current implementation. Severity describes the risk if the application is exposed beyond an isolated classroom environment; deployment context can affect actual exploitability.

## Findings

| # | Severity | File | Lines | Vulnerability | Confidence |
|---|----------|------|-------|---------------|------------|
| 1 | 🟠 HIGH | [config.py](./config.py), [app.py](./app.py) | config.py:19; app.py:20, 49-74, 106-107 | The default Flask signing key is fixed and known. Since authorization trusts the role stored in the signed session, a forged session could impersonate an Admin if the default is active. | 9/10 |
| 2 | 🟠 HIGH | [app.py](./app.py), [login.html](./templates/login.html), [config.py](./config.py), [setup_db.py](./setup_db.py) | app.py:111-114; login.html:6, 8-9; config.py:20; setup_db.py:74-79 | The unauthenticated login page displays the shared seed-account password and account information. Seed accounts receive that same password, so a visitor can authenticate as a listed account, potentially with elevated privileges. | 9/10 |
| 3 | 🟡 MEDIUM | [app.py](./app.py) | app.py:107 | The post-login redirect uses the `next` query parameter without validating that it is a local destination, allowing an external redirect after successful authentication. | 9/10 |

## Remediation status

- **Finding 1 — fixed locally:** `config.py` no longer has a hard-coded signing-key fallback and raises a clear startup error if `SECRET_KEY` is absent. The local ignored `.env` already defines this variable. Deployments must provide a strong, randomly generated key.
- **Finding 2 — partially fixed locally:** the login page no longer pre-fills the seed email/password or lists seed accounts, and `setup_db.py` no longer prints the shared password. However, the shared demo password remains defined in `config.py` and documented in the existing README for coursework compatibility. Treat the seed credentials as demo-only; before deploying or publishing the project, remove/rotate the shared credential and update the setup/test documentation.
- **Finding 3 — not changed:** external redirect validation remains a follow-up because only the two HIGH findings were selected for remediation.

### 1. Predictable Flask signing key

`config.py` supplies a fixed fallback when `SECRET_KEY` is not set, and `app.py` assigns it to Flask. Flask session contents are signed with this key. The role checks trust the role stored in the session, so anyone who knows the fallback can potentially forge a session claiming an elevated role.

**Recommendation:** Require a cryptographically random secret from deployment configuration and fail startup if it is absent. Do not use a fixed development fallback in shared deployments. Rotate the key if it may have been used outside a local demo; existing sessions will then need to be reissued.

### 2. Shared seed credential disclosed to anonymous visitors

The login route supplies seed account information and the configured demo password to the login template, which renders it without requiring authentication. The setup script assigns that shared password to seed accounts whose database hashes are placeholders. This defeats the practical benefit of password hashing for those accounts: their shared plaintext is disclosed by the application itself.

**Recommendation:** Do not render passwords on login pages. Keep seeded demo accounts confined to isolated test databases; disable or replace their credentials before any shared deployment. Use unique credentials and an account-provisioning or reset flow.

### 3. Unvalidated post-login redirect

After a successful login, the route passes `request.args.get("next")` directly to `redirect()`. An attacker can craft a login URL whose `next` parameter points outside the application.

**Recommendation:** Accept only a validated same-origin relative path, and fall back to the dashboard for invalid or external targets.

## Controls observed

- Password checks use Werkzeug's `check_password_hash`; user creation and seed setup use `generate_password_hash`.
- SQL values are generally supplied as PyMySQL parameters rather than concatenated into SQL.
- The concepts endpoint accepts predefined demo keys and typed parameters rather than browser-supplied SQL. Table and procedure names are allowlisted.
- POST requests are protected by a CSRF token check.
- Route decorators distinguish authenticated, write-capable, and Admin-only operations.

These controls reduce risk but do not alone make the application production-ready. In particular, the shared seed credential remains intended only for an isolated demo.

## Additional hardening recommendations

These are defense-in-depth recommendations rather than separately validated exploitable findings:

- The database configuration defaults to connecting as `root` with an empty password. Use a dedicated database account with only the permissions the app needs.
- The Flask entry point enables debug mode. Disable debug mode outside local development; use a production WSGI server, HTTPS, and secure session-cookie settings for shared deployments.
- Keep real database credentials and deployment secrets in protected environment configuration. The local `.env` file was not inspected or included in this audit.

## Remediation boundary

Only the selected signing-key and login-page disclosure changes were made in application files. The external redirect, database configuration, demo credential lifecycle, SQL, and database records were not changed.
