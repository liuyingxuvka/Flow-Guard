"""Read a bounded slice from one complete FlowGuard JSON artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from flowguard.artifact_slices import ArtifactSliceError, read_artifact_slice


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--field", required=True, help="Dotted JSON array field, e.g. surfaces")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
    try:
        result = read_artifact_slice(
            args.artifact,
            field=args.field,
            offset=args.offset,
            limit=args.limit,
        )
    except ArtifactSliceError as exc:
        print(json.dumps({"schema_version": "flowguard.artifact_slice.v1", "status": "blocked", "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
