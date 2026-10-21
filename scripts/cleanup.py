"""List or remove generated artifacts older than the configured retention.

The default is a dry run.  Deletion requires ``--apply`` and is restricted to
the generated chip/overlay/cache directories under the repository data root.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--apply", action="store_true", help="actually remove eligible generated files")
    args = parser.parse_args()
    if args.days < 1:
        raise SystemExit("--days must be positive")

    root = args.data_dir.resolve()
    allowed = {root / "chips", root / "overlays", root / "raw", root / "cache"}
    cutoff = time.time() - args.days * 86400
    candidates = []
    for directory in allowed:
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and path.stat().st_mtime < cutoff:
                candidates.append(path)
    if args.apply:
        for path in candidates:
            path.unlink()
    print({"data_dir": str(root), "days": args.days, "apply": args.apply, "eligible": len(candidates),
           "removed": len(candidates) if args.apply else 0})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
