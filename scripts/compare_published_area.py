"""Compare annual DeforestWatch backfill areas with the published reference.

The input may be the fixture backfill while the live database is unavailable,
but the output labels that evidence as fixture-derived.  This script does not
call the result "accuracy"; the published figure is an external estimate.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoi", default="hasdeo-pekb")
    parser.add_argument("--from", dest="start", type=int, default=2013)
    parser.add_argument("--to", dest="end", type=int, default=2025)
    parser.add_argument("--published-ha", type=float, required=True)
    parser.add_argument("--input", default="data/backfill/hasdeo-pekb.json")
    parser.add_argument("--output", default="data/evaluation/published_area.csv")
    args = parser.parse_args()

    source = Path(args.input)
    if not source.is_file():
        raise SystemExit(f"backfill input not found: {source}; run the fixture or live backfill first")
    rows = json.loads(source.read_text(encoding="utf-8"))
    selected = [row for row in rows if args.start <= int(row["year"]) <= args.end]
    if not selected or any(row.get("status") != "succeeded" for row in selected):
        raise SystemExit("the requested backfill range is incomplete or contains failed runs")

    cumulative = 0.0
    output_rows = []
    for row in sorted(selected, key=lambda item: item["year"]):
        year = int(row["year"])
        sensor = "L8" if year <= 2016 else "S2"
        if "hectares_detected" not in row:
            raise SystemExit("backfill lacks hectares_detected; regenerate it with the current pipeline")
        hectares = float(row["hectares_detected"])
        cumulative += hectares
        output_rows.append({"year": year, "sensor": sensor, "detected_ha": round(hectares, 4), "cumulative_ha": round(cumulative, 4)})

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["year", "sensor", "detected_ha", "cumulative_ha"])
        writer.writeheader()
        writer.writerows(output_rows)

    gap_ha = cumulative - args.published_ha
    gap_pct = gap_ha / args.published_ha * 100 if args.published_ha else None
    print(json.dumps({
        "aoi": args.aoi,
        "source": str(source),
        "evidence": "fixture_backfill" if "backfill" in source.parts else "live_or_external_backfill",
        "years": [args.start, args.end],
        "cumulative_detected_ha": round(cumulative, 4),
        "published_reference_ha": args.published_ha,
        "difference_ha": round(gap_ha, 4),
        "difference_percent": round(gap_pct, 4) if gap_pct is not None else None,
        "table": str(output),
        "interpretation": "comparison with an external estimate; not an accuracy claim",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
