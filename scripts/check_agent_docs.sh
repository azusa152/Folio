#!/usr/bin/env bash
# Verify the two AGENTS.md files each carry a cross-reference to the other.
# Prevents silent drift where one file is updated and the other loses its pointer.
#
# Exit 0 = OK.  Exit 1 = missing cross-reference (prints which file is affected).
set -euo pipefail

ROOT_DOC="AGENTS.md"
AGENT_DOC="docs/agents/AGENTS.md"
FAILED=0

if ! grep -q 'docs/agents/AGENTS.md' "$ROOT_DOC"; then
  echo "ERROR: $ROOT_DOC is missing cross-reference to $AGENT_DOC" >&2
  FAILED=1
fi

if ! grep -q '\.\./\.\./AGENTS\.md' "$AGENT_DOC"; then
  echo "ERROR: $AGENT_DOC is missing cross-reference to $ROOT_DOC" >&2
  FAILED=1
fi

if [ "$FAILED" -eq 0 ]; then
  echo "Agent doc cross-references OK"
fi

exit "$FAILED"
