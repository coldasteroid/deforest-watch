"""Export auditable alert feedback into a retraining manifest.

The API appends one JSON object per line to the feedback log.  This command
filters and copies those records into a dated, machine-readable manifest; it
does not invent geometry or labels, so a downstream training job can require
the corresponding alert chip before using a record.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/labels/feedback/feedback.jsonl")
    parser.add_argument("--output", default=None)
    parser.add_argument("--verdict", choices=("verified", "false_positive"), default=None)
    args = parser.parse_args()

    source = Path(args.input)
    if not source.is_file():
        raise SystemExit(f"feedback log not found: {source}")
    records = []
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid JSON on feedback line {line_number}: {exc}") from exc
        if args.verdict is None or record.get("verdict") == args.verdict:
            records.append(record)

    output = Path(args.output) if args.output else source.with_name(f"manifest-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    print(json.dumps({"input": str(source), "output": str(output), "records": len(records), "verdict": args.verdict}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
