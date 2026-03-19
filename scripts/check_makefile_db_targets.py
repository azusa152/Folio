"""Ensure DB maintenance Make targets run inside Docker."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
MAKEFILE = ROOT / "Makefile"

TARGETS = (
    "refresh-eligible",
    "migrate-ledger",
    "migrate-ledger-dry",
    "purge-legacy",
    "purge-legacy-dry",
)
REQUIRED_SNIPPET = "docker compose exec backend"


def _extract_target_command(make_text: str, target: str) -> str | None:
    # Capture recipe body until the next top-level target declaration.
    pattern = rf"^{re.escape(target)}\s*:.*\n((?:^\t.*\n)+)"
    match = re.search(pattern, make_text, flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def main() -> int:
    if not MAKEFILE.exists():
        print(f"ERROR: Makefile not found: {MAKEFILE}")
        return 1

    make_text = MAKEFILE.read_text(encoding="utf-8")
    failures: list[str] = []

    for target in TARGETS:
        command = _extract_target_command(make_text, target)
        if command is None:
            failures.append(f"- Missing target: {target}")
            continue
        if REQUIRED_SNIPPET not in command:
            failures.append(
                f"- Target '{target}' must run in Docker "
                f"(expected snippet: '{REQUIRED_SNIPPET}')"
            )

    if failures:
        print("Makefile DB target contract check FAILED:")
        for failure in failures:
            print(failure)
        return 1

    print(
        "Makefile DB target contract check passed — all DB maintenance targets run in Docker."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
