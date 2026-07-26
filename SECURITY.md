# Security Policy

Variorum connects to GitHub repositories and reads source code, so security is a
first-class concern. This document describes the security model and how to report a
vulnerability responsibly.

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Report suspected vulnerabilities privately using GitHub's
[private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
on this repository (**Security → Report a vulnerability**), or by contacting the
maintainer directly via [emdanish.dev](https://emdanish.dev).

When reporting, please include:

- a description of the issue and its impact,
- steps to reproduce (proof-of-concept if possible),
- affected component (frontend, backend, GitHub integration, AI layer), and
- any suggested remediation.

You can expect an initial acknowledgement within a few days. Please give a reasonable
window to investigate and ship a fix before any public disclosure.

## Security principles

Variorum is designed around a few non-negotiable principles:

- **Least privilege.** The GitHub App requests only the permissions it needs, and
  operates with short-lived, per-installation tokens.
- **Human-in-the-loop.** Variorum *proposes* changes; a human reviews and merges. It
  never auto-merges and never force-pushes. Generated changes always land on a dedicated
  branch and open a pull request against the default branch.
- **Ownership scoping.** Every API resource is scoped to the authenticated user; cross
  -tenant access returns `404` (no resource-existence disclosure).
- **No secrets in the repository.** `.env`, `*.pem`, `*.key`, and `secrets/` are
  git-ignored. Secrets are supplied via environment variables and validated at startup.
- **Fail closed.** Missing webhook secret ⇒ signature verification fails; unset critical
  config in production ⇒ the backend refuses to start.

## What is protected, and how

| Area | Control |
|---|---|
| **Authentication** | GitHub OAuth via the App; server-side sessions signed with `SESSION_SECRET`. Cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` in production. |
| **Authorization** | Resources are scoped by `GitHubInstallation.owner_user_id`; unauthorized access returns `404`. |
| **Webhooks** | HMAC-SHA256 signature over the raw body, compared in constant time (`hmac.compare_digest`), enforced before any processing. |
| **GitHub tokens** | Installation tokens are cached in memory only — never persisted to the database, disk, or logs. App JWTs are RS256-signed with the private key. |
| **Transport / CORS** | CORS is a strict allowlist (never `*` with credentials). HSTS is sent in production. |
| **HTTP headers** | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, and `Permissions-Policy` on every response (both frontend and backend). |
| **Rate limiting** | In-process abuse protection on auth, webhook, and AI endpoints. For production, pair with edge/gateway rate limiting. |
| **Error handling** | Clients receive generic messages; full error detail is logged server-side only. A catch-all handler guarantees no stack trace leaks. |
| **SQL** | All database access uses SQLAlchemy ORM / parameterized queries — no string-built SQL. |
| **Secrets in code** | No `eval`/`exec`/`os.system`/`shell=True`; AI output is parsed and validated, never executed. |

## Data handling and AI providers

To analyze a repository, Variorum sends **source code and pull-request diffs to
third-party AI providers** (Google Gemini, DeepSeek, Perplexity) over TLS. This is
inherent to the product. Note:

- Diffs and code are sent to the provider APIs, **not** written to logs (logs contain
  only provider/model/latency metadata).
- There is no automatic scrubbing of secrets that may appear inside a diff. Treat the
  configured AI providers as trusted processors of your repository content, and avoid
  connecting repositories whose diffs routinely contain live credentials.
- AI output is treated as untrusted input: it is parsed, coerced, and clamped, and is
  only ever proposed to a human as a pull request — never executed or written to a
  protected branch.

## Supported versions

Variorum is under active development. Security fixes are applied to the `main` branch.
