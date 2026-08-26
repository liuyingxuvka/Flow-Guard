"""Publish the direct-current persistent reverse-surface owner authority."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from flowguard.reverse_surface_owner_authority import (
    REVERSE_SURFACE_OWNER_AUTHORITY_RELATIVE_PATH,
    build_current_reverse_surface_owner_authority,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--model-parent-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    artifact = build_current_reverse_surface_owner_authority(
        args.root,
        model_parent_receipt=args.model_parent_receipt,
    )
    output = (
        args.output
        if args.output is not None
        else Path(args.root) / REVERSE_SURFACE_OWNER_AUTHORITY_RELATIVE_PATH
    )
    if output.resolve() != (Path(args.root) / REVERSE_SURFACE_OWNER_AUTHORITY_RELATIVE_PATH).resolve():
        raise ValueError("persistent reverse owner authority must use its canonical current path")
    print(
        json.dumps(
            {
                "status": artifact["status"],
                "artifact_fingerprint": artifact["artifact_fingerprint"],
                "discovery_fingerprint": artifact["discovery_fingerprint"],
                "owner_routes": artifact["owner_routes"],
                "owner_receipt_ids": [
                    row["receipt_id"] for row in artifact["owner_receipt_identities"]
                ],
                "output": str(output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
