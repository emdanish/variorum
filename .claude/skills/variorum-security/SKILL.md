---
name: variorum-security
description: Use for anything security-sensitive in Variorum — authentication, sessions, API authorization, secrets handling, GitHub App permissions/tokens, webhook verification, or secure coding. Apply before merging auth/secrets/GitHub changes.
---

# Variorum security conventions

## Authentication & sessions
- Users authenticate via **GitHub OAuth (user-to-server)** with CSRF `state` (compared with `secrets.compare_digest`).
- Session is a signed cookie (`SessionMiddleware`): `https_only` in production, `same_site="lax"`. `SESSION_SECRET` must be a strong random value in prod (startup fails on the default).
- Identity is keyed **strictly on `github_user_id`** — never link/merge accounts by email.

## Authorization
- Every resource is scoped to its owner. Load via ownership-checked queries; never act on a client-supplied id without verifying the current user owns it.
- **Installation owner-guard:** `upsert_installation` never reassigns an installation to a different owner; `setup_callback` requires login and confirms ownership.

## Secrets
- Never commit secrets — `.env`, `*.pem`, `secrets/` are git-ignored. **Verify with `git check-ignore` before committing.**
- Never log tokens/keys or request bodies. Send the Gemini API key via the `x-goog-api-key` **header**, never the URL query string.
- GitHub App private key comes from a file path or base64 env var; installation tokens are short-lived and cached in memory only.

## GitHub App
- Least privilege: Contents (read/write for PRs), Pull requests (read/write), Metadata (read). No admin scopes.
- Webhooks: verify `X-Hub-Signature-256` HMAC in **constant time**, fail closed on missing secret/signature.
- **Human-in-the-loop:** generated PRs target non-protected branches; never auto-merge or force-push.

## Practice
- Run the built-in **`security-review`** skill before merging changes to auth, secrets, GitHub integration, or webhook handling.
- Validate all input at the boundary (Pydantic). No raw SQL string interpolation — always bound parameters via SQLAlchemy.
