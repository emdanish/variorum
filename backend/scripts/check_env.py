"""Validate the .env configuration for a Variorum demo.

Run from the backend directory:  python scripts/check_env.py
Prints a checklist (never printing secret values) and a demo-readiness verdict.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.core.config import get_settings  # noqa: E402


def _mark(ok: bool) -> str:
    return "OK  " if ok else "MISSING"


def main() -> int:
    s = get_settings()
    print("Variorum environment check\n" + "=" * 40)

    # Database
    db_ok = False
    try:
        from app.db.session import engine

        with engine.connect() as conn:
            conn.execute(text("select 1"))
        db_ok = True
    except Exception as exc:  # noqa: BLE001
        db_reason = str(exc)[:80]
    print(f"[{_mark(db_ok)}] Database reachable ({s.database_url.split('@')[-1]})")
    if not db_ok:
        print(f"         -> {db_reason}")

    # AI providers
    ai_keys = {
        "GEMINI_API_KEY_1": s.gemini_api_key_1,
        "GEMINI_API_KEY_2": s.gemini_api_key_2,
        "DEEPSEEK_API_KEY": s.deepseek_api_key,
        "PERPLEXITY_API_KEY": s.perplexity_api_key,
    }
    configured = [k for k, v in ai_keys.items() if v]
    print(f"[{_mark(bool(configured))}] AI provider keys: {', '.join(configured) or 'none'}")
    print("         (run 'python scripts/check_ai.py' to test them live)")

    # GitHub App
    private_key = bool(s.github_app_private_key_base64) or (
        bool(s.github_app_private_key_path)
        and Path(s.github_app_private_key_path).is_file()
    )
    checks = {
        "GITHUB_APP_ID": bool(s.github_app_id),
        "GITHUB_APP_SLUG": bool(s.github_app_slug),
        "GITHUB_APP_CLIENT_ID": bool(s.github_app_client_id),
        "GITHUB_APP_CLIENT_SECRET": bool(s.github_app_client_secret),
        "GITHUB_WEBHOOK_SECRET": bool(s.github_webhook_secret),
        "GitHub App private key": private_key,
    }
    for name, ok in checks.items():
        print(f"[{_mark(ok)}] {name}")

    session_ok = s.session_secret != "dev-insecure-session-secret-change-me"
    print(f"[{_mark(session_ok)}] SESSION_SECRET changed from default")

    github_ready = all(
        [checks["GITHUB_APP_ID"], private_key, checks["GITHUB_APP_CLIENT_ID"],
         checks["GITHUB_APP_CLIENT_SECRET"]]
    )
    demo_ready = db_ok and bool(configured) and github_ready
    print("=" * 40)
    if demo_ready:
        print("READY: database, AI keys, and GitHub App are all configured.")
    else:
        print("NOT READY yet. Fill the MISSING items above (see SETUP.md).")
    return 0 if demo_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
