# Variorum — Setup & Demo Guide

This is the complete, click-by-click guide to configure Variorum and run a live
MVP demo. Follow it top to bottom. It assumes Windows (PowerShell); notes for
macOS/Linux are included where they differ.

**The demo does NOT require a public webhook tunnel.** You trigger pull-request
analysis with an **Analyze** button in the app, so everything runs against
`localhost`.

---

## 0. What you need (already installed on this machine)

- Python 3.11+ · Node.js 20+ · PostgreSQL 17 (native) · Git
- Your AI provider keys (already in `.env`, verified working)

You only need to add **GitHub App** credentials. That's what this guide walks
through.

---

## 1. One-time database setup (already done — for reference)

Variorum uses a local PostgreSQL database named `variorum` with a role
`variorum`. This was already created. If you ever need to recreate it, run in a
`psql` shell as the `postgres` superuser:

```sql
CREATE ROLE variorum LOGIN PASSWORD 'variorum' CREATEDB;
CREATE DATABASE variorum OWNER variorum;
```

The schema is created automatically by the start script (`alembic upgrade head`).

> The `DATABASE_URL` in `.env` already points here:
> `postgresql+psycopg://variorum:variorum@localhost:5432/variorum`

---

## 2. Create the GitHub App (≈ 5 minutes)

A **GitHub App** (not an OAuth App) lets Variorum read your code and open pull
requests with least-privilege, per-installation access.

### 2.1 Open the "New GitHub App" page

- For your **personal** account:
  open **https://github.com/settings/apps** → click **New GitHub App**.
- (For an organization: `https://github.com/organizations/YOUR_ORG/settings/apps`
  → **New GitHub App**.)

If prompted, confirm your password.

### 2.2 Fill in the form

Fill these fields exactly (leave everything else at its default):

| Field | Value |
|---|---|
| **GitHub App name** | `variorum-<yourname>` (must be globally unique; e.g. `variorum-danish`) |
| **Homepage URL** | `http://localhost:3000` |
| **Callback URL** | `http://localhost:8000/api/v1/auth/github/callback` |
| **Setup URL (optional)** | `http://localhost:8000/api/v1/github/setup` |
| **Redirect on update** | ✅ check this box (right under Setup URL) |

**Webhooks:** Find the **Webhook** section and **UNCHECK "Active"**.
(You don't need webhooks for the demo — the app has an Analyze button. If you
want live webhooks later, see §7.)

### 2.3 Set permissions

Scroll to **Permissions → Repository permissions** and set:

| Permission | Access |
|---|---|
| **Contents** | **Read and write** |
| **Pull requests** | **Read and write** |
| **Metadata** | Read-only (this is selected automatically) |

Leave all other permissions as **No access**.

### 2.4 Installation scope

Under **"Where can this GitHub App be installed?"** choose **Only on this
account**.

### 2.5 Create it

Click **Create GitHub App**. You'll land on the App's settings page. Keep this
tab open — the next step reads values from it.

---

## 3. Collect the credentials and generate a private key

Still on your new App's settings page:

1. **App ID** — near the top ("App ID: 123456"). Copy the number.
2. **Client ID** — just below ("Client ID: Iv1.abc123..."). Copy it.
3. **Client secret** — click **Generate a new client secret**. Copy the value
   **now** (GitHub shows it only once).
4. **App slug** — look at the page URL:
   `https://github.com/settings/apps/`**`variorum-yourname`** — that last part is
   the slug.
5. **Private key** — scroll to **Private keys** → click **Generate a private
   key**. A `.pem` file downloads (e.g. `variorum-yourname.2026-07-26.private-key.pem`).
   - Move that file to: **`D:\GitHub\variorum\backend\secrets\github-app.pem`**
     (create the `secrets` folder if it doesn't exist; it is git-ignored).

---

## 4. Fill in `.env`

Open **`D:\GitHub\variorum\.env`** in a text editor. It already has your AI keys
and database URL. Fill in the GitHub section using what you collected in §3.
Here is exactly what each variable is and where its value came from:

```dotenv
# --- GitHub App ---
GITHUB_APP_ID=123456                         # §3.1  the "App ID" number
GITHUB_APP_SLUG=variorum-yourname            # §3.4  the slug from the App URL
GITHUB_APP_CLIENT_ID=Iv1.abc123def456        # §3.2  the "Client ID"
GITHUB_APP_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxx  # §3.3  the generated client secret
GITHUB_WEBHOOK_SECRET=                        # leave blank (webhooks off for demo)
GITHUB_APP_PRIVATE_KEY_PATH=./secrets/github-app.pem   # §3.5  path to the .pem
GITHUB_APP_PRIVATE_KEY_BASE64=                # leave blank (using the path above)
```

Notes:
- `GITHUB_APP_PRIVATE_KEY_PATH` is **relative to the `backend/` folder**, so
  `./secrets/github-app.pem` means `backend/secrets/github-app.pem`.
- Every other value in `.env` is already set correctly — **do not change** the
  AI keys, `DATABASE_URL`, `SESSION_SECRET`, or the URLs.
- Never commit `.env` — it is git-ignored.

Reference for the values you should NOT need to touch (already set):

```dotenv
DATABASE_URL=postgresql+psycopg://variorum:variorum@localhost:5432/variorum
BACKEND_PUBLIC_URL=http://localhost:8000     # must match the App's Callback/Setup URLs
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000
GEMINI_API_KEY_1=... GEMINI_API_KEY_2=... DEEPSEEK_API_KEY=... PERPLEXITY_API_KEY=...
GEMINI_MODEL=gemini-flash-latest
DEEPSEEK_MODEL=deepseek-v4-flash
PERPLEXITY_MODEL=sonar
```

---

## 5. Verify your configuration

From `D:\GitHub\variorum\backend` (activate the venv first, or use the full
path shown):

```powershell
.\.venv\Scripts\python.exe scripts\check_env.py
```

You want every line to say `OK`. Then test the AI providers live:

```powershell
.\.venv\Scripts\python.exe scripts\check_ai.py
```

At least one provider must say `OK` (all four should).

---

## 6. Start everything and run the demo

### 6.1 Start both services (one command)

From `D:\GitHub\variorum`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-all.ps1
```

This opens **two windows**: the backend (`http://localhost:8000`) and the
frontend (`http://localhost:3000`). Leave them running.

> On macOS/Linux/Git Bash: run `scripts/start-backend.sh` and
> `scripts/start-frontend.sh` in two terminals.

> **Important:** if you edit `.env` again, **restart the backend window**
> (Ctrl+C, then re-run the script) so it picks up the new values.

### 6.2 The demo, step by step

1. Open **http://localhost:3000/dashboard**.
2. The status cards should show **Backend: ok**, **AI providers: …**,
   **GitHub App: configured**.
3. Click **Sign in with GitHub** → authorize the app. You return to the
   dashboard, signed in.
4. Click **Connect repository** → GitHub opens → choose the repository you want
   to demo (pick one with a Markdown doc that describes some code) → **Install**.
   You're redirected back; the repo appears in the list.
5. Click **Index** next to the repo. Watch the badge go
   `pending → indexing → indexed` (the page auto-refreshes).
6. On GitHub, open a **pull request** on that repo that changes code the docs
   describe (e.g., rename a documented function, change an auth flow). Note the
   **PR number**.
7. Back in the dashboard, type the PR number in the **PR #** box next to the
   repo and click **Analyze**.
8. Within a few seconds a **Documentation drift** finding appears — severity,
   summary, the affected doc, and PR number.
9. Click **Open doc-fix PR**. Variorum creates a branch, commits an updated
   doc, and opens a pull request. Click **View PR** to show it on GitHub.

That's the full loop: **connect → understand → detect (with evidence) →
propose a fix**.

### 6.3 A good demo repository

Pick a small repo where a doc references code, for example a README that says
*"authentication uses session cookies"* next to an `auth.py`. Then open a PR that
changes `auth.py` to JWT. Variorum will flag the README and propose the fix.

---

## 7. (Optional) Live webhooks instead of the Analyze button

If you want pull requests to be analyzed automatically on open (no button):

1. Install a tunnel, e.g. [smee.io](https://smee.io): click **Start a new
   channel**, copy the URL (e.g. `https://smee.io/abc123`).
2. In your GitHub App settings → **Webhook**: check **Active**, set the
   **Webhook URL** to the smee URL, set a **Webhook secret** (any long random
   string) and put the same value in `.env` as `GITHUB_WEBHOOK_SECRET`.
   Under **Subscribe to events**, check **Pull request**, **Push**,
   **Installation**, and **Installation repositories**. Save.
3. Run the smee forwarder so events reach your backend:
   ```powershell
   npx smee-client --url https://smee.io/abc123 --target http://localhost:8000/webhooks/github
   ```
4. Restart the backend. Now opening a PR triggers analysis automatically.

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| Dashboard says "GitHub App: incomplete" | A value in `.env` is missing/typo'd. Run `check_env.py`. Restart backend after edits. |
| "Sign in with GitHub" does nothing / 503 | `GITHUB_APP_CLIENT_ID`/`SECRET` missing, or backend not restarted after editing `.env`. |
| After install, no repos appear | Make sure you clicked **Connect repository** *while signed in*; the private key path must be correct (`check_env.py`). |
| Analyze returns no findings | The PR must change code that a doc references (see §6.3). Also confirm the repo finished **indexing**. |
| "Open doc-fix PR" → 502 | The App needs **Contents: Read & write** and **Pull requests: Read & write** permissions (§2.3). Re-check, then in the repo's install settings accept the updated permissions. |
| Backend won't start | Run `check_env.py`; ensure PostgreSQL is running and `DATABASE_URL` is correct. |

---

## 9. Quick command reference

```powershell
# Verify config / providers
cd D:\GitHub\variorum\backend
.\.venv\Scripts\python.exe scripts\check_env.py
.\.venv\Scripts\python.exe scripts\check_ai.py

# Start both services
cd D:\GitHub\variorum
powershell -ExecutionPolicy Bypass -File scripts\start-all.ps1

# Backend API docs
#   http://localhost:8000/docs
# App
#   http://localhost:3000/dashboard
```
