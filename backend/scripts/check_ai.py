"""Ping each configured AI provider with the user's real keys.

Run from the backend directory:  python scripts/check_ai.py
Reports, per provider: configured?, works?, latency, and any error. Useful
before a demo to confirm keys and model names are valid.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.base import Message, ProviderError  # noqa: E402
from app.ai.service import build_provider_manager  # noqa: E402
from app.core.config import get_settings  # noqa: E402


async def main() -> int:
    settings = get_settings()
    manager = build_provider_manager(settings)
    providers = manager._providers  # noqa: SLF001 — diagnostics tool
    prompt = [Message(role="user", content="Reply with the single word: ok")]

    print("Provider          Configured  Result")
    print("-" * 60)
    any_ok = False
    for provider in providers:
        if not provider.is_configured:
            print(f"{provider.name:<17} no          (skipped — no API key)")
            continue
        try:
            # Generous budget: some models (e.g. Gemini thinking models) spend
            # output tokens on reasoning before emitting any text.
            result = await provider.complete(prompt, max_tokens=512)
            any_ok = True
            snippet = result.text.strip().replace("\n", " ")[:40]
            print(
                f"{provider.name:<17} yes         OK  {provider.model}  "
                f"({result.latency_ms} ms)  -> {snippet!r}"
            )
        except ProviderError as exc:
            print(f"{provider.name:<17} yes         FAIL [{exc.kind.value}] {exc}")
        except Exception as exc:  # noqa: BLE001
            print(f"{provider.name:<17} yes         ERROR {type(exc).__name__}: {exc}")

    print("-" * 60)
    print("At least one provider works." if any_ok else "No provider is working!")
    return 0 if any_ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
