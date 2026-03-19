from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _run_smart_scan(
    tmp_path: Path,
    *,
    dow: int,
    hour_utc: int,
    now_epoch: int,
    last_epoch: int,
    market_stale: int,
    off_hours_stale: int,
) -> str:
    repo_root = Path(__file__).resolve().parents[3]
    script_path = repo_root / "docker/scanner/smart-scan.sh"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    calls_file = tmp_path / "calls.log"

    _write_executable(
        fake_bin / "date",
        """#!/bin/sh
if [ "$1" = "+%u" ]; then
  echo "${TEST_DOW}"
elif [ "$1" = "-u" ] && [ "$2" = "+%H" ]; then
  echo "${TEST_HOUR_UTC}"
elif [ "$1" = "+%s" ]; then
  echo "${TEST_NOW_EPOCH}"
else
  /bin/date "$@"
fi
""",
    )
    _write_executable(
        fake_bin / "jq",
        """#!/bin/sh
sed -n 's/.*"epoch"[[:space:]]*:[[:space:]]*\\([0-9][0-9]*\\).*/\\1/p'
""",
    )
    _write_executable(
        fake_bin / "folio-curl.sh",
        """#!/bin/sh
echo "$@" >> "${TEST_CALLS_FILE}"
case "$*" in
  *"/scan/last"*)
    echo "{\\"epoch\\": ${TEST_LAST_EPOCH}}"
    ;;
  *)
    echo "{}"
    ;;
esac
""",
    )

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}:{env.get('PATH', '')}",
            "TEST_DOW": str(dow),
            "TEST_HOUR_UTC": f"{hour_utc:02d}",
            "TEST_NOW_EPOCH": str(now_epoch),
            "TEST_LAST_EPOCH": str(last_epoch),
            "TEST_CALLS_FILE": str(calls_file),
            "SCAN_STALE_SECONDS_MARKET_HOURS": str(market_stale),
            "SCAN_STALE_SECONDS_OFF_HOURS": str(off_hours_stale),
        }
    )

    subprocess.run(["sh", str(script_path)], check=True, env=env)
    return calls_file.read_text(encoding="utf-8")


def test_smart_scan_should_trigger_when_market_hours_age_exceeds_configured_threshold(
    tmp_path: Path,
) -> None:
    calls = _run_smart_scan(
        tmp_path,
        dow=2,  # Tue
        hour_utc=14,  # Market-hours window in script
        now_epoch=1000,
        last_epoch=850,
        market_stale=120,
        off_hours_stale=3600,
    )
    assert "/scan/last" in calls
    assert "-X POST http://backend:8000/scan" in calls


def test_smart_scan_should_skip_when_off_hours_age_is_under_configured_threshold(
    tmp_path: Path,
) -> None:
    calls = _run_smart_scan(
        tmp_path,
        dow=6,  # Sat
        hour_utc=10,
        now_epoch=1000,
        last_epoch=700,
        market_stale=120,
        off_hours_stale=500,
    )
    assert "/scan/last" in calls
    assert "-X POST http://backend:8000/scan" not in calls
