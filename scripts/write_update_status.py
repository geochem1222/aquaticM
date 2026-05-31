#!/usr/bin/env python3
"""Write workflow update diagnostics into data/update-status.json."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default="data/update.log")
    parser.add_argument("--status-code", default="")
    parser.add_argument("--output", default="data/update-status.json")
    args = parser.parse_args()

    log_path = Path(args.log)
    output = Path(args.output)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status_code": args.status_code,
        "log_tail": redact(tail(log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else "", 12000)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def tail(value: str, size: int) -> str:
    return value[-size:]


def redact(value: str) -> str:
    value = re.sub(r"s2k-[A-Za-z0-9_-]+", "s2k-[REDACTED]", value)
    value = re.sub(r"x-api-key['\"]?:\\s*['\"][^'\"]+['\"]", "x-api-key: [REDACTED]", value, flags=re.IGNORECASE)
    return value


if __name__ == "__main__":
    main()
