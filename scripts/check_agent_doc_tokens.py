"""
Check token budgets for AI agent docs.

Approximation:
  tokens ~= words / 0.75

Exit 1 when any tracked document exceeds its configured budget.
"""

import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

DOC_BUDGETS: dict[str, int] = {
    "AGENTS.md": 500,
    "docs/agents/AGENTS.md": 500,
    "docs/agents/TOOLS.md": 500,
    "docs/agents/folio/SKILL.md": 1200,
}


def estimate_tokens(text: str) -> int:
    """Estimate token count from word count."""
    words = len(re.findall(r"\S+", text))
    return math.ceil(words / 0.75)


def main() -> None:
    errors: list[str] = []

    for rel_path, budget in DOC_BUDGETS.items():
        abs_path = ROOT / rel_path
        if not abs_path.exists():
            errors.append(f"missing file: {rel_path}")
            continue

        tokens = estimate_tokens(abs_path.read_text())
        if tokens > budget:
            errors.append(f"{rel_path}: {tokens} tokens (budget: {budget})")
        else:
            print(f"{rel_path}: {tokens} tokens (budget: {budget})")

    if errors:
        print("Agent doc token budget check FAILED:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print("Agent doc token budget check passed.")


if __name__ == "__main__":
    main()
